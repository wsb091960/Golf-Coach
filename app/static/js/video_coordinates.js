(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.VideoCoordinates=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  function containRect(elementRect,mediaWidth,mediaHeight){
    const boxWidth=Number(elementRect&&elementRect.width)||0;
    const boxHeight=Number(elementRect&&elementRect.height)||0;
    const sourceWidth=Number(mediaWidth)||0;
    const sourceHeight=Number(mediaHeight)||0;
    if(boxWidth<=0||boxHeight<=0||sourceWidth<=0||sourceHeight<=0)return null;
    const scale=Math.min(boxWidth/sourceWidth,boxHeight/sourceHeight);
    const width=sourceWidth*scale;
    const height=sourceHeight*scale;
    return {
      left:(Number(elementRect.left)||0)+(boxWidth-width)/2,
      top:(Number(elementRect.top)||0)+(boxHeight-height)/2,
      width,
      height
    };
  }

  function clientToMediaPoint(clientX,clientY,elementRect,mediaWidth,mediaHeight){
    const rect=containRect(elementRect,mediaWidth,mediaHeight);
    if(!rect)return null;
    const x=(Number(clientX)-rect.left)/rect.width;
    const y=(Number(clientY)-rect.top)/rect.height;
    if(!Number.isFinite(x)||!Number.isFinite(y)||x<0||x>1||y<0||y>1)return null;
    return [x,y];
  }

  return {containRect,clientToMediaPoint};
});
