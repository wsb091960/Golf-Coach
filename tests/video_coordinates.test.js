const test=require('node:test');
const assert=require('node:assert/strict');
const {containRect,clientToMediaPoint}=require('../app/static/js/video_coordinates.js');

test('maps portrait-video clicks through the visible contained image',()=>{
  const element={left:100,top:50,width:1600,height:900};
  const media=containRect(element,900,1600);
  assert.deepEqual(media,{left:646.875,top:50,width:506.25,height:900});
  const point=clientToMediaPoint(media.left+media.width*0.2,media.top+media.height*0.3,element,900,1600);
  assert.ok(Math.abs(point[0]-0.2)<1e-12);
  assert.ok(Math.abs(point[1]-0.3)<1e-12);
});

test('maps landscape clicks without adding an offset',()=>{
  const element={left:10,top:20,width:1280,height:720};
  assert.deepEqual(clientToMediaPoint(330,200,element,1920,1080),[0.25,0.25]);
});

test('rejects clicks in portrait-video side bars',()=>{
  const element={left:0,top:0,width:1600,height:900};
  assert.equal(clientToMediaPoint(200,450,element,900,1600),null);
});
