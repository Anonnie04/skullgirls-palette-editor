using System.Diagnostics;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using System.Runtime.Loader;
using SkullgirlsModManager;

try
{
    using var configuration = JsonDocument.Parse(File.ReadAllText(args[0]));
    string managerRoot = Path.GetFullPath(configuration.RootElement.GetProperty("ManagerRoot").GetString()!);
    string assemblies = File.Exists(Path.Combine(managerRoot, "dist", "Core.dll")) ? Path.Combine(managerRoot, "dist") : managerRoot;
    if (!File.Exists(Path.Combine(assemblies, "Core.dll"))) throw new Exception("Mod Manager's Core.dll is missing. Choose its installation folder.");
    AssemblyLoadContext.Default.Resolving += (context, name) =>
    {
        string candidate = Path.Combine(assemblies, name.Name + ".dll");
        return File.Exists(candidate) ? context.LoadFromAssemblyPath(candidate) : null;
    };
    Apply(args);
}
catch (Exception ex) { Console.Error.WriteLine(ex.Message); Environment.ExitCode = 1; }

static void Apply(string[] args)
{
try
{
    var request = JsonSerializer.Deserialize<Request>(File.ReadAllText(args[0])) ?? throw new Exception("Invalid apply request.");
    string root = Path.GetFullPath(request.ManagerRoot), operation = Path.GetDirectoryName(Path.GetFullPath(args[0]))!;
    if (!Directory.Exists(Path.Combine(root, "Mods")) || !Directory.Exists(Path.Combine(root, "Data")))
        throw new Exception("Choose the Skullgirls Mod Manager folder containing Mods and Data.");
    if (Process.GetProcessesByName("SkullGirls").Length != 0) throw new Exception("Close Skullgirls before applying a palette.");
    var library = new Library(Path.Combine(root, "Mods"));
    var manager = new Manager(request.GameFolder, Path.Combine(root, "Data"));
    if (manager.NeedsRecovery) throw new Exception("Recover the interrupted operation in Mod Manager first.");
    if (!manager.DataFolder.Equals(Path.GetFullPath(request.DataFolder), StringComparison.OrdinalIgnoreCase))
        throw new Exception("The active game folder changed. Reload the palette before applying.");
    foreach (var (key, hash) in request.Expected)
        if (Convert.ToHexString(SHA256.HashData(ReadAsset(manager.DataFolder, key))).ToLowerInvariant() != hash)
            throw new Exception("Game assets changed after preparation. Reload the palette and try again.");
    var mods = library.Mods();
    string identity = "paletteeditor.direct." + request.Character;
    var previous = mods.SingleOrDefault(m => m.Info.Id == identity);
    if (mods.Count(m => m.Info.Id == identity) > 1) throw new Exception("Multiple direct palette mods found.");
    ArchiveCompatibility.Require(manager.GameFolder, new[] { "characters-foits.gfs", "sprites.gfs" });
    var existingPlan = manager.Preview(mods);
    // Do not silently fold pending character metadata changes into an old snapshot.
    string foit = "characters/" + request.Character + ".foit";
    if (existingPlan.Replacements.TryGetValue("characters-foits.gfs", out var replacements) && replacements.TryGetValue(foit, out string? planned)
        && !ReadAsset(manager.DataFolder, "characters-foits.gfs/" + foit).AsSpan().SequenceEqual(File.ReadAllBytes(planned)))
        throw new Exception("Apply pending character mods in Mod Manager, then reload this palette before applying directly.");
    byte[] currentMetadata = ReadAsset(manager.DataFolder, "characters-foits.gfs/" + foit);
    byte[] baseline = currentMetadata;
    bool retainPrevious = previous?.Enabled == true;
    if (retainPrevious)
    {
        string recorded = Path.Combine(previous!.Folder, "baseline.foit");
        if (!File.Exists(recorded)) throw new Exception("Reload this character after disabling its old direct-palette mod in Mod Manager.");
        baseline = File.ReadAllBytes(recorded);
        var withoutDirect = manager.Preview(mods.Where(m => m.Folder != previous.Folder));
        byte[] otherMetadata;
        if (withoutDirect.Replacements.TryGetValue("characters-foits.gfs", out var others) && others.TryGetValue(foit, out string? other)) otherMetadata = File.ReadAllBytes(other);
        else otherMetadata = ReadAsset(File.Exists(Path.Combine(manager.BackupFolder, "characters-foits.gfs")) ? manager.BackupFolder : manager.DataFolder, "characters-foits.gfs/" + foit);
        if (!otherMetadata.AsSpan().SequenceEqual(baseline))
            throw new Exception("Another character mod changed. Disable this character's direct-palette mod, apply the other mods in Mod Manager, then reload the palette.");
    }
    string? oldFolder = previous?.Folder;
    string backup = Path.Combine(operation, "previous-direct-mod");
    string orderFile = Path.Combine(library.Root, "order.json");
    byte[]? oldOrder = File.Exists(orderFile) ? File.ReadAllBytes(orderFile) : null;
    Mod? imported = null;
    bool committed = false;
    try
    {
        if (previous != null)
        {
            if (!Path.GetFullPath(previous.Folder).StartsWith(library.Root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new Exception("Invalid mod path.");
            Directory.Move(previous.Folder, backup);
        }
        using (var zip = ZipFile.Open(request.Zip, ZipArchiveMode.Update))
        {
            var entry = zip.GetEntry("mod.json") ?? throw new Exception("Mod details are missing.");
            Dictionary<string, JsonElement> fields;
            using (var input = entry.Open()) fields = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(input)!;
            fields["id"] = JsonSerializer.SerializeToElement(identity);
            entry.Delete();
            using var output = zip.CreateEntry("mod.json").Open();
            JsonSerializer.Serialize(output, fields);
        }
        imported = library.Import(request.Zip);
        // Retain DDS replacements for earlier edited slots of this character.
        if (retainPrevious)
            foreach (string source in Library.Walk(Path.Combine(backup, "sprites.gfs")))
            {
                string relative = Path.GetRelativePath(backup, source);
                string destination = Path.Combine(imported.Folder, relative);
                if (!File.Exists(destination)) { Directory.CreateDirectory(Path.GetDirectoryName(destination)!); File.Copy(source, destination); }
            }
        string infoPath = Path.Combine(imported.Folder, "mod.json");
        var info = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(File.ReadAllText(infoPath))!;
        info["id"] = JsonSerializer.SerializeToElement(identity);
        File.WriteAllText(infoPath, JsonSerializer.Serialize(info, new JsonSerializerOptions { WriteIndented = true }));
        imported = new Mod(imported.Folder);
        File.WriteAllBytes(Path.Combine(imported.Folder, "baseline.foit"), baseline);
        imported.SetEnabled(true);
        var snapshot = mods.Where(m => m.Folder != oldFolder).Append(imported).ToList();
        library.SetOrder(snapshot);
        manager.Log = Console.WriteLine;
        manager.Apply(snapshot);
        committed = true;
        foreach (var archive in imported.Replacements())
            foreach (var asset in archive.Value)
                if (!ReadAsset(manager.DataFolder, archive.Key + "/" + asset.Key).AsSpan().SequenceEqual(File.ReadAllBytes(asset.Value)))
                    throw new Exception("Installed palette verification failed: " + asset.Key);
        File.WriteAllText(Path.Combine(operation, "result.json"), JsonSerializer.Serialize(new { status = "passed", mod = imported.Folder, backups = manager.BackupFolder, data = manager.DataFolder }));
        Console.WriteLine("Palette installed and verified. Backups retained.");
    }
    catch
    {
        if (!committed)
        {
            if (imported != null && Directory.Exists(imported.Folder)) Directory.Move(imported.Folder, Path.Combine(operation, "failed-mod"));
            if (oldFolder != null && Directory.Exists(backup)) Directory.Move(backup, oldFolder);
            if (oldOrder != null) File.WriteAllBytes(orderFile, oldOrder);
            else if (File.Exists(orderFile)) File.Delete(orderFile);
        }
        throw;
    }
}
catch (Exception ex) { Console.Error.WriteLine(ex.Message); Environment.ExitCode = 1; }
}

static byte[] ReadAsset(string folder, string route)
{
    int split = route.IndexOf('/');
    var index = Archives.Read(Path.Combine(folder, route[..split]));
    var entry = index.Entries.Single(e => e.Path == route[(split + 1)..]);
    using var input = File.OpenRead(index.FilePath); input.Position = entry.Offset;
    byte[] bytes = new byte[checked((int)entry.Size)]; input.ReadExactly(bytes); return bytes;
}

record Request(string ManagerRoot, string GameFolder, string DataFolder, string Character, string Zip, Dictionary<string, string> Expected);
