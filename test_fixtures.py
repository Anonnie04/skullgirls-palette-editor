"""Synthetic game assets used only by the editor tests."""
import io, struct
import numpy as np
from PIL import Image

def make_gfs(path,entries):
 def string(s):b=s.encode();return struct.pack('>Q',len(b))+b
 table=string('Reverge Package File')+string('1.1')+struct.pack('>Q',len(entries))
 for name,data in entries.items():table+=string(name)+struct.pack('>QI',len(data),1)
 path.write_bytes(struct.pack('>I',len(table)+4)+table+b''.join(entries.values()))

def fixture(root):
 game=root/'FixtureGame';data=game/'data01';data.mkdir(parents=True);arts={5:bytearray(),4:bytearray()};frames=[]
 def image(bank,flags=58,variant=0):
  index=np.tile(np.array([1,1,2,2]*4,np.uint8),(16,1));g=np.tile(np.arange(16,dtype=np.uint8)*2,(16,1))
  if variant:index=np.flip(index,axis=1).copy()
  streams=[bytes(256),g.tobytes(),index.tobytes()];encoded=[bytes([126])+len(b).to_bytes(2,'big')+b for b in streams]
  offset=len(arts[bank]);arts[bank].extend(b''.join(encoded))
  if bank==4:arts[bank].append(0xbb)
  return dict(n=1,w=1,h=1,used=1,flags=flags,mask='01',offset=offset,sizes=tuple(map(len,encoded)))
 def record(bank,images):
  result=struct.pack('<2iBBB',0,0,bank,0,sum(1<<k for k in images))
  for k,m in sorted(images.items()):result+=struct.pack('<4HB',1,1,1,1,m['flags'])+b'\x01'+struct.pack('<4i',m['offset'],*m['sizes'])
  return result+bytes(46)
 m0=image(5);m1=image(5,variant=1);m2=image(4,122);m3=image(5);overlay=image(5,variant=1)
 frames=[record(5,{0:m0}),record(5,{0:m1}),record(4,{0:m2}),record(5,{0:m3,1:overlay}),record(5,{0:m1})]
 palette=np.zeros((4,16,4),np.uint8)
 for row,color in [(1,(100,160,220)),(2,(200,210,180)),(3,(220,45,45))]:
  for x in range(16):palette[row,x,:3]=np.array(color)*(.35+.65*x/15);palette[row,x,3]=255
 from game_palette import weights
 counts=(1,5,5,5)
 def gradient(swap=False):
  raw=bytearray();expanded=[]
  for row,count in enumerate(counts):
   points=np.array([np.interp(np.linspace(0,15,count),np.arange(16),palette[row,:,ch]) for ch in range(4)]).T
   points=np.rint(points).astype(np.uint8)
   if swap:points[:,:3]=points[:,[1,2,0]]
   raw.extend(points[::-1,[2,1,0,3]].tobytes());expanded.append(np.floor(weights(count)@points).astype(np.uint8))
  dds=io.BytesIO();Image.fromarray(np.array(expanded)).save(dds,format='DDS')
  return bytes(raw),dds.getvalue()
 first,dds1=gradient();second,dds2=gradient(True)
 table=b'\x05Annie'+struct.pack('<IBHB',60,1,2,4)
 for row,count in enumerate(counts):
  label=f'material {row}'.encode();table+=struct.pack('<BHB',count,0,len(label))+label
 table+=b'\x00'+first+bytes(8)+b'variable effect data\x00'+second+bytes(8)+b'end palette data\x00'
 foit=struct.pack('<I',16)+b'VRSN'+struct.pack('<I',9)+bytes(4)+table+b'\x01'+struct.pack('<I',len(frames))+b''.join(frames)
 make_gfs(data/'characters-art.gfs',{'characters/annie.art':bytes(arts[5])});make_gfs(data/'characters-art-pt.gfs',{'characters/annie.art-pt':bytes(arts[4])});make_gfs(data/'characters-foits.gfs',{'characters/annie.foit':foit});make_gfs(data/'sprites.gfs',{'sprites/annie_1p.dds':dds1,'sprites/annie_2p.dds':dds2})
 return game
