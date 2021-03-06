"""This file is part of DeepLens which is released under MIT License and 
is copyrighted by the University of Chicago. This project is developed by
the database group (chidata).

vdmsio.py uses the VDMS client to add and find videos. It contains
primitives to encode and decode archived and regular video formats.
"""
from dlstorage.core import *
from dlstorage.constants import *
from dlstorage.stream import *
from dlstorage.header import *
from dlstorage.xform import *
from dlstorage.utils.clip import *

import vdms
import json
import cv2 #it looks like there's no choice but to use opencv because we need 
#to convert frames to seconds, or vice versa, and so we need the fps of 
#the original video
import multiprocessing as mp
import math
import itertools
import numpy as np
from PIL import Image
import io

def url2Disk(vstream, \
             fname):
#            video = cv2.VideoCapture(filename)
#            #Find OpenCV version
#            (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')
#            if int(major_ver) < 3:
#                frame_rate = video.get(cv2.cv.CV_CAP_PROP_FPS)
#            else:
#                frame_rate = video.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    urllst = fname.split('/')
    file_name = urllst[-1]
    frame_rate = 30

    start = True
    for frame in vstream:
        if start:
            out = cv2.VideoWriter(file_name,
                                  fourcc, 
                                  frame_rate, 
                                  (vstream.width, vstream.height),
                                  True)
            start = False
        out.write(frame['data'])
    out.release()

def add_video(fname, \
              vname, \
              vstream, \
              encoding, \
              header):
    
    tags = []
    totalFrames = 0
    height = -1
    width = -1
    start = True
    for i,frame in enumerate(vstream):
        header.update(frame)
        if start == True:
            height = vstream.height
            width = vstream.width
            start = False
        tags.append(frame['tags'])
        totalFrames = i
    
    db = vdms.vdms()
    db.connect('localhost')
    fd = open(fname, 'rb')
    blob = fd.read()
    all_queries = []
    addVideo = {}
    addVideo["container"] = "mp4"
    """
    if encoding == H264:
        addVideo["codec"] = "h264"
    else:
        addVideo["codec"] = "xvid"
        Actually, I think you can only use h264 on VDMS
    """
    addVideo["codec"] = "h264"
    header_dat = header.getHeader()
    props = {}
    props[0] = header_dat
    props[0]["isFull"] = True
    props[0]["name"] = vname
    props[0]["width"] = width
    props[0]["height"] = height
    #addVideo["properties"] = props
    vprops = {}
    vprops["name"] = vname
    vprops["isFull"] = True
    addVideo["properties"] = vprops
    query = {}
    query["AddVideo"] = addVideo
    all_queries.append(query)
    response, res_arr = db.query(all_queries, [[blob]])
    #print(response)
    db.disconnect()
    return totalFrames,props

def add_video_clips(fname, \
                    vname, \
                    vstream, \
                    encoding, \
                    header, \
                    size):

    tags = []

    video = cv2.VideoCapture(fname)
    #Find OpenCV version
    (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')
    if int(major_ver) < 3:
        fps = video.get(cv2.cv.CV_CAP_PROP_FPS)
    else:
        fps = video.get(cv2.CAP_PROP_FPS)
    
    numFrames = int(fps * size)
    #print("numFrames in clip: " + str(numFrames))
    counter = 0
    clipCnt = 0
    props = {}
    vprops = {}
    totalFrames = 0
    height = -1
    width = -1
    start = True
    for i,frame in enumerate(vstream):
        totalFrames += 1
        if start == True:
            height = vstream.height
            width = vstream.width
    if totalFrames <= numFrames:
        return add_video(fname, vname, vstream, encoding, header)

    for i,frame in enumerate(vstream):
        header.update(frame)
        tags.append(frame['tags'])
        
        if counter == numFrames:
            props[clipCnt] = header.getHeader()
            props[clipCnt]["clipNo"] = clipCnt #add a clip number for easy
            props[clipCnt]["width"] = width
            props[clipCnt]["height"] = height
            #retrieval
            props[clipCnt]["numFrames"] = numFrames
            props[clipCnt]["isFull"] = False
            props[clipCnt]["name"] = vname
            header.reset()
            ithprops = {}
            ithprops["clipNo"] = clipCnt
            ithprops["name"] = vname
            ithprops["isFull"] = False
            vprops[clipCnt] = ithprops
            counter = 0
            clipCnt += 1
        counter += 1
    #print("totalFrames in clip: " + str(totalFrames))
    
    db = vdms.vdms()
    db.connect('localhost')
    fd = open(fname, 'rb')
    blob = fd.read()
    all_queries = []
    addVideo = {}
    addVideo["container"] = "mp4"
    if encoding == H264:
        addVideo["codec"] = "h264"
    else:
        addVideo["codec"] = "xvid"
    
    if size > 0:
        addVideo["clipSize"] = size
    
    addVideo["accessTime"] = 2
    
    addVideo["properties"] = vprops
    #print("properties of clip: " + str(vprops))
    
    query = {}
    query["AddVideoBL"] = addVideo
    all_queries.append(query)
    response, res_arr = db.query(all_queries, [[blob]])
    #print(response)
    db.disconnect()
    return totalFrames,props
    

def find_clip(vname, \
               condition, \
               size, \
               headers, \
               clip_no, \
               isFull):
    
    db = vdms.vdms()
    db.connect("localhost")
    
    all_queries = []
    findVideo = {}
    constrs = {}
    constrs["name"] = ["==", vname]
    if isFull:
        constrs["isFull"] = ["==", isFull]
    else:
        constrs["clipNo"] = ["==", clip_no]
    #add more filters based on the conditions
    
    findVideo["constraints"] = constrs
    findVideo["container"] = "mp4"
    findVideo["codec"] = "h264"
    
    query = {}
    query["FindVideo"] = findVideo
    
    all_queries.append(query)
    response, vid_arr = db.query(all_queries)
    #print(response)
    db.disconnect()
    return vid_arr

def find_frame(x,y,vname,isFull):
    db = vdms.vdms()
    db.connect("localhost")
    
    all_queries = []
    findFrames = {}
    xToy = range(x, y + 1)
    xToylst = list(xToy)
    findFrames["frames"] = xToylst
    constrs = {}
    constrs["name"] = ["==", vname]
    if isFull:
        constrs["isFull"] = ["==", isFull]
    
    findFrames["constraints"] = constrs
    query = {}
    query["FindFrames"] = findFrames
    
    all_queries.append(query)
    #print("Issuing Query to find frames Between: " + str(x) + "," + str(y))
    #print(all_queries)
    response, res_arr = db.query(all_queries)
    db.disconnect()
    
    return res_arr

#return the sequence of frames representing the clip
#Precondition: the video was stored in its entirety,
#rather than as clips.
def find_clip2(vname, \
               condition, \
               size, \
               headers, \
               clip_no, \
               isFull, \
               totalFrames, \
               height, \
               width, \
               threads):
    
    start = clip_no * size
    end = (clip_no + 1)*size
    if end >= totalFrames:
        end = totalFrames - 1
    tsize = end - start
    #numCores = mp.cpu_count() - 1 
    #numCores = 3 #3 seems to be the limit
    numCores = threads
    psize = int(math.ceil(tsize / numCores))
    #print("Number of frames per part: " + str(psize))
    endpts = list()
    for i in range(0, numCores):
        xp = start + i * psize
        yp = start + (i+1)*psize
        if yp >= totalFrames:
            yp = totalFrames - 1
        endpts.append((xp,yp))
    pool = mp.Pool(mp.cpu_count() - 1)
    results = pool.starmap(find_frame, [(x,y,vname,isFull) for (x,y) in endpts])
    pool.close()
    
    #properly unpack results
    imgs = list(itertools.chain.from_iterable(results))
    
    #convert from byte string to opencv image array
    img_arrs = []
    for img in imgs:
        #OpenCV solution: currently fails due to TypeError: Expected Ptr<cv::UMat> for argument '%s'
        #nparr = np.fromstring(img, np.uint8)
        #nparr = np.frombuffer(bytearray(img), dtype=np.uint8)
        #img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # cv2.IMREAD_COLOR in OpenCV 3.1
        #img_unp = cv2.UMat(img_np)

        #img_ipl = cv2.cv.CreateImageHeader((img_np.shape[1], img_np.shape[0]), cv.IPL_DEPTH_8U, 3)
        #cv2.cv.SetData(img_ipl, img_np.tostring(), img_np.dtype.itemsize * 3 * img_np.shape[1])

        #PIL solution
        img_bytes = io.BytesIO(bytes(img))
        img_obj = Image.open(img_bytes)
        #img_np = img_obj.getdata()
        img_np = np.array(img_obj)
        
        img_arrs.append(img_np)
    
    return frames2Clip(vname, start, end, clip_no, img_arrs)
    
    

def frames2Clip(vname, \
               start, \
               end, \
               clipNo, \
               imgs):
#    start = True
    imstream = IteratorVideoStream(imgs)
#    for img in imstream:
#        height = imstream.height
#        width = imstream.width
#        size = (width,height)
#        if start == True:
#            out = cv2.VideoWriter(vname + str(clipNo) + 'tmp.mp4', cv2.VideoWriter_fourcc(*'XVID'), 30, size)
#            start = False
#        out.write(img['data'])
#        
#    out.release()
    return imstream

def find_video(vname, \
               condition, \
               size, \
               headers, \
               totalFrames, \
               threads):
    
    clips = clip_boundaries(0, totalFrames-1, size)
    print("find_video Clips: " + str(clips)) #should only be one clip: the full video
    boundaries = []
    streams = []
    relevant_clips = set()
    #vid_arr is an array of video blobs, which we can't use in this case.
    #Therefore, we have to write them to disk first and then materialize them
    #using pre-stored header info and 
    
    if headers[0]["isFull"]:
        """
        then, find_frame already returns the correct result stream, so no
        extra work to do
        """
        height = headers[0]["height"]
        width = headers[0]["width"]
        itrvidstream = find_clip2(vname, condition, size, headers, 0, True, totalFrames, height, width, threads)
        return itrvidstream
        
    for i in range(len(headers)):
        header_data = headers[i]
        isFull = header_data["isFull"]
        height = header_data["height"]
        width = header_data["width"]
        itrvidstream = find_clip2(vname, condition, size, headers, i, isFull, totalFrames, height, width, threads)
        nFrames = sum(1 for i in itrvidstream)
        print("itrvidstream has " + str(nFrames))
        if condition(header_data):
            print("Start Frame: " + str(header_data['start']))
            print("End Frame: " + str(header_data['end']))
            pstart, pend = find_clip_boundaries((header_data['start'], \
                                                 header_data['end']), \
                                                 clips)
            print("pstart: " + str(pstart))
            print("pend: " + str(pend))
        
    
    
            relevant_clips.update(range(pstart, pend+1))
            boundaries.append((header_data['start'],header_data['end']))
        
        streams.append(itrvidstream)
    
    relevant_clips = sorted(list(relevant_clips))
    
    return [materialize_clip(clips[i], boundaries, streams) for i in relevant_clips]
