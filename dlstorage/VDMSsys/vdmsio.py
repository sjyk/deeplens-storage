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
from dlstorage.VDMSsys.correctclipDPAlg import *

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
import random
import os

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
    if numCores > 1:
        psize = int(math.ceil(tsize / numCores))
        #print("Number of frames per part: " + str(psize))
        endpts = list()
        for i in range(0, numCores):
            xp = start + i * psize
            yp = start + (i+1)*psize
            if yp >= totalFrames:
                yp = totalFrames - 1
                endpts.append((xp,yp))
        #This is the correct code for parallelization, but when we don't need
        #parallelization, and we just want to run single-threaded execution,
        #we should just call the find_frame function directly--that's my guess.
        pool = mp.Pool(numCores)
        results = pool.starmap(find_frame, [(x,y,vname,isFull) for (x,y) in endpts])
        pool.close()
        
        #properly unpack results
        imgs = list(itertools.chain.from_iterable(results))
    else:
        imgs = find_frame(start,end,vname,isFull)
    
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
    boundaries = []
    streams = []
    relevant_clips = set()
    #vid_arr is an array of video blobs, which we can't use in this case.
    #Therefore, we have to write them to disk first and then materialize them
    #using pre-stored header info and 
    print("header length: " + str(len(headers)))
    for i in range(len(headers)):
        header_data = headers[i]
        isFull = header_data["isFull"]
        height = header_data["height"]
        width = header_data["width"]
        itrvidstream = find_clip2(vname, condition, size, headers, i, isFull, totalFrames, height, width, threads)
        if  not any(True for _ in itrvidstream):
            print("Empty itrvidstream object returned!")
        else:
            numFrames = sum(1 for i in itrvidstream)
            print("Stream Size: " + str(numFrames))
        if condition(header_data):
            pstart, pend = find_clip_boundaries((header_data['start'], \
                                                 header_data['end']), \
                                                 clips)
    
            relevant_clips.update(range(pstart, pend+1))
            boundaries.append((header_data['start'],header_data['end']))
        
        streams.append(itrvidstream)
    
    relevant_clips = sorted(list(relevant_clips))
    
    return [materialize_clip(clips[i], boundaries, streams) for i in relevant_clips]

"""
Non-uniform clip size methods
"""

def find_clipNU(vname, \
               condition, \
               headers, \
               clip_no, \
               start, \
               end, \
               isFull, \
               totalFrames, \
               height, \
               width, \
               threads):
    if end >= totalFrames:
        end = totalFrames - 1
    tsize = end - start
    #numCores = mp.cpu_count() - 1 
    #numCores = 3 #3 seems to be the limit
    numCores = threads
    if numCores > 1:
        psize = int(math.ceil(tsize / numCores))
        #print("Number of frames per part: " + str(psize))
        endpts = list()
        for i in range(0, numCores):
            xp = start + i * psize
            yp = start + (i+1)*psize
            if yp >= totalFrames:
                yp = totalFrames - 1
                endpts.append((xp,yp))
        #This is the correct code for parallelization, but when we don't need
        #parallelization, and we just want to run single-threaded execution,
        #we should just call the find_frame function directly--that's my guess.
        pool = mp.Pool(numCores)
        results = pool.starmap(find_frame, [(x,y,vname,isFull) for (x,y) in endpts])
        pool.close()
        
        #properly unpack results
        imgs = list(itertools.chain.from_iterable(results))
    else:
        imgs = find_frame(start,end,vname,isFull)
    
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

"""
Find all clips satisfying the given condition, with no assumptions
about the clip size: that is, the video need not be uniformly partitioned.
"""
def find_vid_NU(vname, \
                  condition, \
                  condName, \
                  headers, \
                  totalFrames, \
                  threads):
    """
    all the clip processing from before is needed only if you divided the video
    into uniform clips, and now need to retrieve a part that doesn't necessarily
    match up with a single clip, and could span multiple clips.
    this also means that we cannot find the clip boundaries initially: we need
    to find them as we consider whether clips satisfy conditions or not
    """
    #condName is a dictionary of subconditions whose conjunction forms the total
    #condition
    
    if "startsAfter" in condName and "endsBefore" in condName:
        start = condName["startsAfter"]
        end = condName["endsBefore"]
    else:
        print("Operation Unsupported: query must be a simple temporal predicate")
        return None
    
    target = (start,end)
    #get all clips that were stored in this execution of DeepLens
    clips = []
    for i in range(len(headers)):
        header_data = headers[i]
        clips.append((header_data['start'], header_data['end']))
    
    ivsObjs = clips_in_range(clips, target)
    cost, ptree = dp_alg(ivsObjs, target)
    trtag = tagTree(ptree, 0)
    oclips = findLeaves(ptree) #get the original clips
    #figure out what the clips to be retrieved look like when they are cropped
    pushDownCrop(ptree)
    #get the intervals representing the cropped clips
    ret_clips = findLeaves(ptree)
    sclips = sorted(ret_clips, key=lambda x: x[1][0])
    #retrieve the clips the intervals represent from the database!
    
    """
    NOTE: the kind of parallelism employed before actually leads to multiple
    FindFrames calls to VDMS for a smaller number of frames-so even though
    the FindFrames queries are being executed in parallel, there's a lot
    more decoding from each call, since I have to decode
    the entire video anyways, so the effect is nullified
    Therefore, we need to parallelize here
    """
    if threads > 1:
        print("TODO")
    else:
        all_queries = []
        for o in oclips:
            cclips = [r for r in ret_clips if r[0] == o[0]]
            cclip = cclips[0]
            x = cclip[1][0] - o[1][0]
            y = cclip[1][1] - o[1][0]
            query = single_frameNU(x,y,vname,o[1])
            all_queries.append(query)
        db = vdms.vdms()
        db.connect("localhost")
        response, res_arr = db.query(all_queries)
        db.disconnect()
        entities = response[0]['FindFrames']['entities']
        rclips = []
        for e in entities:
            st = e['start']
            en = e['end']
            rclips.append((st, en))
        
        streams = []
        for j,s in enumerate(sclips):
            ocs = [o for o in oclips if o[0] == s[0]]
            oc = ocs[0]
            inds = [i for i,c in enumerate(rclips) if c[0] == oc[1][0] and c[1] == oc[1][1]]
            img_arrs = []
            for img in res_arr[inds[0]]:
                #PIL solution
                img_bytes = io.BytesIO(bytes(img))
                img_obj = Image.open(img_bytes)
                #img_np = img_obj.getdata()
                img_np = np.array(img_obj)
                img_arrs.append(img_np)
            imstream = frames2Clip(vname, s[1][0], s[1][1], j, img_arrs)
            streams.append(imstream)
        #merge all the streams and return the result
        return itertools.chain(*streams)
            
            
            
def single_frameNU(x,y,vname, oclip):
    findFrames = {}
    xToy = range(x, y + 1)
    xToylst = list(xToy)
    findFrames["frames"] = xToylst
    constrs = {}
    constrs["name"] = ["==", vname]
    constrs["start"] = ["==", oclip[0]]
    constrs["end"] = ["==", oclip[1]]
    results = {}
    results["list"] = ["start","end"]
    #it's possible that two partitions of a video have a clip in common,
    #but we only want the frames for one clip
    results["limit"] = 1
    findFrames["constraints"] = constrs
    findFrames["results"] = results
    query = {}
    query["FindFrames"] = findFrames
    return query

#gives a unique identifier to each of the leaves
def tagTree(tr, tag):
    if tr.op_str == "retrieve":
        tr.res_int = (tag, tr.res_int)
        return tag+1
    else:
        for c in tr.children:
            tag = tagTree(c, tag)
        return tag

"""
alters clips to be retrieved by cropping intervals to be between tI
"""
def changeLeaves(tr, tI):
    if tr.op_str == "retrieve":
        curI = tr.res_int[1]
        if curI[0] <= tI[0] and curI[1] >= tI[0]:
            tr.res_int[1] = [tI[0], tr.res_int[1][1]] #cut curI to tI[0]
        elif curI[0] <= tI[1] and curI[1] >= tI[1]:
            tr.res_int[1] = [tr.res_int[1][0], tI[1]] #cut curI to tI[1]
        elif curI[0] <= tI[0] and curI[1] >= tI[1]: #cut curI to tI
            tr.res_int[1] = tI
    else:
        for c in tr.children:
            changeLeaves(c,tI)

"""
changes the leaves of the tree so they reflect the crops in the tree
"""
def pushDownCrop(tr):
    #apply previous crops first
    for c in tr.children:
        pushDownCrop(c)
    if tr.op_str == "crop":
        changeLeaves(tr, tr.res_int)

def findLeaves(tr):
    if tr.op_str == "retrieve":
        return [tr.res_int]
    else:
        rlst = []
        for c in tr.children:
            rlst = rlst + findLeaves(c)
        return rlst
    
"""
given a number tfs, generate a random partitioning of the interval [0, tfs]
"""
def genRands(tfs):
    thres = (tfs * 2)/3
    nParts = random.randint(1,thres)
    bPoints = random.sample(range(1,tfs), nParts)
    lst = sorted(bPoints)
    rlst = []
    for i in range(len(lst) - 1):
        rlst.append((bPoints[i], bPoints[i+1]))
    return rlst

"""
This does the same thing as add_video_clips, except
rather than using a fixed size, this function breaks the video into
clips of different sizes randomly, and then stores these clips.
"""
def add_vid_Rand(fname, \
                 vname, \
                 vstream, \
                 encoding, \
                 header):
    tags = []
    
    video = cv2.VideoCapture(fname)
    #Find OpenCV version
    (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')
    if int(major_ver) < 3:
        fps = video.get(cv2.cv.CV_CAP_PROP_FPS)
    else:
        fps = video.get(cv2.CAP_PROP_FPS)
    
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
            start = False
    
    bPoints = genRands(totalFrames)
    curPt = (0,bPoints[0])
    for i,frame in enumerate(vstream):
        header.update(frame)
        tags.append(frame['tags'])
        
        if i == curPt[1][-1] or i == totalFrames - 1:
            props[clipCnt] = header.getHeader()
            props[clipCnt]["clipNo"] = clipCnt #add a clip number for easy
            #retrieval
            props[clipCnt]["width"] = width
            props[clipCnt]["height"] = height
            props[clipCnt]["start"] = curPt[1][0]
            props[clipCnt]["end"] = curPt[1][1]
            props[clipCnt]["isFull"] = False
            props[clipCnt]["name"] = vname
            header.reset()
            ithprops = {}
            ithprops["clipNo"] = clipCnt
            ithprops["name"] = vname
            ithprops["isFull"] = False
            vprops[clipCnt] = ithprops
            curPt = (curPt[0]+1, bPoints[curPt[0]+1])
            clipCnt += 1
    
    db = vdms.vdms()
    db.connect('localhost')
    qlst = []
    blst = []
    clst = []
    for i,b in enumerate(bPoints):
        cname,query,blob = single_Query(vname, vprops[i], b, vstream, encoding)
        qlst.append(query)
        blst.append([blob])
        clst.append(cname)
    response, res_arr = db.query(qlst, blst)
    print(response)
    db.disconnect()
    for c in clst: #clean up the directory
        os.remove(c)
    return totalFrames,props

def single_Query(vname, props, pt, vstream, encoding):
    
    """
    First, we want to write the relevant frames into a clip,
    so we can read that clip out
    """
    for i,frame in enumerate(vstream):
        width = vstream.width
        height = vstream.height
        size = (width, height)
        if i == pt[0]:
            out = cv2.VideoWriter(vname + str(pt[0]) + 'tmp.mp4', cv2.VideoWriter_fourcc(*'XVID'), 30, size)
        if i >= pt[0] and i <= pt[1]:
            out.write(frame['data'])
    out.release()
    
    fname = vname + str(pt[0]) + 'tmp.mp4'
    fd = open(fname, 'rb')
    blob = fd.read()
    addVideo = {}
    addVideo["container"] = "mp4"
    if encoding == H264:
        addVideo["codec"] = "h264"
    else:
        addVideo["codec"] = "xvid"
    
    addVideo["properties"] = props
    #print("properties of clip: " + str(vprops))
    
    query = {}
    query["AddVideo"] = addVideo
    return fname,query,blob
    
    
    
