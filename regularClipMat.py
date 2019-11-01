import sys
import numpy as np

#algorithm: do what materialization currently does right now, given
#cost models for merging and cropping: just find the clips that overlap with the given one
#crop the ends, and then merge all the relevant clips.

#check if i1 is contained in i2
def isIn(i1,i2):
    return i1[0] >= i2[0] and i1[1] <= i2[1]

#compute cost of merging i1 with i2
def est_Single(i1, i2):
    base_ccost = 10
    merge_cost = 20
    if isIn(i1,i2): #if i1 is contained in i2
        print("Why are you comparing")
        print(i1)
        print("to")
        print(i2)
        return -1 #you should be cropping, not merging
    if isIn(i2,i1): #if i2 is contained in i1
        print("Why are you comparing")
        print(i1)
        print("to")
        print(i2)
        return -1 #you should be cropping, not merging
    if i1[0] - i2[1] < 0 and i1[1] - i2[1] > 0:
        crop_cost = abs(i1[0] - i2[1]) * base_ccost
    elif i2[0] - i1[1] < 0 and i2[1] - i1[1] > 0:
        crop_cost = abs(i2[0] - i1[1]) * base_ccost
    else:
        crop_cost = 0
    tot_cost = merge_cost + crop_cost
    return tot_cost

#compute cost of cropping i1 into i2
def crop_Cost(i1,i2):
    if isIn(i2,i1):
        base_ccost = 10
        return (i2[0] - i1[0] + i1[1] - i2[1])*base_ccost
    return -1

#return the cost of materializing the given clip, given the bounds of the
#clips already stored in the backend.
def mat_clip(clip,bounds):
    start_b = -1
    end_b = -1
    for i,b in enumerate(bounds):
        if b[0] <= clip[0] and b[1] >= clip[0]:
            start_b = i
        if b[0] <= clip[1] and b[1] >= clip[1]:
            end_b = i
    rel_clips = bounds[start_b:end_b+1]
    #now, just materialize across
    cur_cost = 0
    if len(rel_clips) == 1:
        cur_cost = crop_Cost(rel_clips[0], clip)
        return cur_cost
    
    cur_clip = rel_clips[0]
    for i,r in enumerate(rel_clips):
        if i == 0:
            continue
        cur_cost += est_Single(cur_clip, r)
        if r[0] < cur_clip[0]:
            lb = r[0]
        else:
            lb = cur_clip[0]
        if r[1] > cur_clip[1]:
            rb = r[1]
        else:
            rb = cur_clip[1]
        cur_clip = (lb,rb)
    if cur_clip[0] < clip[0] and cur_clip[1] > clip[1]:
        cur_cost += crop_Cost(cur_clip, clip)
    return cur_cost,cur_clip
        
        
    
    
#no storage of multiple partitions-because there's no reason for you to do that
#if you're only going to store your clips with fixed size.
ivs = [(0,2),(2,4),(4,6),(6,8),(8,10),(10,12),(12,14),(14,16),(16,18),(18,20)]
i1 = [3,17]
cst,clip = mat_clip(i1,ivs)
print("Materialization Cost: " + str(cst))
print("Materialized Clip: " + str(clip))