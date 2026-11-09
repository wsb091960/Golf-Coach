"""Generate provisional ten-frame swing candidates from decoded video motion.

This is motion-window detection, NOT validated P1-P10 recognition. Coach review
is mandatory before using frames as biomechanical evidence.
"""
from pathlib import Path
import cv2
import numpy as np

def propose_frames(video_path: Path) -> list[int]:
    cap=cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Video could not be decoded")
    try:
        count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if count < 30:
            raise ValueError("Video needs at least 30 decoded frames")
        stride=max(1, count//220)
        indices=[]
        scores=[]
        previous=None
        # Sequential decoding avoids expensive repeated keyframe seeks on mobile MP4.
        index=0
        while index<count:
            if index % stride:
                if not cap.grab(): break
                index+=1
                continue
            ok,frame=cap.read()
            if not ok: break
            gray=cv2.cvtColor(cv2.resize(frame,(160,90)),cv2.COLOR_BGR2GRAY)
            gray=cv2.GaussianBlur(gray,(5,5),0)
            if previous is not None:
                # Robust difference: suppress compression noise and minor flicker.
                diff=cv2.absdiff(gray,previous)
                scores.append(float(np.mean(np.maximum(diff.astype(np.float32)-12,0))))
                indices.append(index)
            previous=gray
            index+=1
        if len(scores)<12: raise ValueError("Insufficient decodable video frames")
        smooth=np.convolve(np.asarray(scores),np.ones(5)/5,mode="same")
        peak=float(np.max(smooth))
        if peak<0.7:
            raise ValueError("No clear movement detected; select frame indices manually")
        active=np.flatnonzero(smooth>max(0.7,peak*0.18))
        if len(active)<5: raise ValueError("Movement interval is too short")
        # Use the dominant contiguous movement region, bridging short pauses.
        runs=[];start=int(active[0]);last=start
        for i in active[1:]:
            i=int(i)
            if i-last>max(3,round(0.08*len(scores))):
                runs.append((start,last));start=i
            last=i
        runs.append((start,last))
        a,b=max(runs,key=lambda pair: float(np.sum(smooth[pair[0]:pair[1]+1])))
        # Include pre-motion address and follow-through, but avoid long idle sections.
        margin=max(2,round((b-a)*0.09))
        first=max(0,indices[max(0,a-margin)]-stride)
        last=min(count-1,indices[min(len(indices)-1,b+margin)])
        if last-first<20: raise ValueError("Detected swing interval too short")
        # Ten ordered, distinct candidates. NOT P-position classification.
        result=np.rint(np.linspace(first,last,10)).astype(int).tolist()
        if len(set(result))!=10: raise ValueError("Not enough unique frames")
        return result
    finally:
        cap.release()
