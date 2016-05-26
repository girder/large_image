#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

import argparse
import math
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
np.set_printoptions(threshold=np.nan)
import requests

URL=0
NUM_LEVELS=1
NUM_X_TILES=2
NUM_Y_TILES=3
ATLAS_ARR=4
def main():
    #source.txt
    file_name='source.txt'
    run_params={}
    with open(file_name,'r') as params:
        for line in params:
            args=line.split()
            run_params[args[0]]=args
    for host in run_params.keys():
        if host=='atlas':
            print "getiing atlas"
            elapsed_time=get_data("atlas",'atlas hardcoded img',int(run_params[host][1]))
        elif host=='adrc':
            print "getting adrc data"
            elapsed_time=get_data("adrc",'adrc hardcoded img',int(run_params[host][1]))
        else:
            print"getting girder"
            elapsed_time=get_data(run_params[host][0],run_params[host][1],int(run_params[host][2]))
        run_params[host].append(elapsed_time)
        
    plot_data_and_save(run_params)           
def get_data(host,image_id,requested_levels):
      
    total_tiles=0
    num_levels=-1
    data={}
    request_time=-1
    if host=="atlas":
        image_id='atlas_data_base'
        data=atlas_init()
    elif host=="adrc":
        image_id='adrc_data_base'
        data=adrc_init()
    else:
        data=girder_init(host,image_id)
    num_levels=data[NUM_LEVELS]
    #if sucessful begin to grab tiles form each level
    if num_levels!=-1:
        if requested_levels>num_levels:
            requested_levels=num_levels
        #initialize numpy array of max size including padding
        for z in range(requested_levels):
            total_tiles+=2**(z*2)
              
        count=0
        elapsed_time_arr=np.zeros([total_tiles], dtype=float)
        #collect from all levels
        for z in range(requested_levels):
            print"started level %d"%(z)
           
            
            
            for x in range (2**z):
                for y in range(2**z):

                    if host=="atlas":
                        
                        request_time=atlas_request(data,z,x,y)
                    elif host=="adrc":
                        
                        request_time=adrc_request(data,z,x,y)
                    else:
                       
                        request_time=girder_request(data,z,x,y)
                    if request_time!=-1:
                        elapsed_time_arr[count]=request_time
                        count+=1
                    
        #create a new array of correct size and plot
        elapsed_arr_final=np.zeros([count], dtype=float) 
        np.copyto(elapsed_arr_final,elapsed_time_arr[:count])
        return elapsed_arr_final
        
def adrc_init():
    data={}
    data[URL]="http://digitalslidearchive.emory.edu/fcgi-bin/iipsrvOpenslide.fcgi?DeepZoom=/GLOBAL_SCRATCH/PREUSS_LAB/BATCH1/19775.svs_files/%d/%d_%d.jpg"
    data[NUM_LEVELS]=10
    return data
def atlas_init():

    data={}    
    num_level=9    
    image_id='500c3e674834a3119800000c'
    database_id='5074589002e31023d4292d83'
    data[URL]="https://slide-atlas.org/tile?img={img_id}&db={db_id}&name=%s.jpg".format(img_id=image_id,db_id=database_id)
    data[NUM_LEVELS]=num_level
    pos_list=[]
    
    base=np.arr=np.empty((2,2),dtype=str)
    base[0,0]='q'
    base[0,1]='r'
    base[1,0]='t'
    base[1,1]='s'
    for level in range(num_level):
        level_arr=np.empty(((2**level),(2**level)),dtype='|S%s'%(level+1))
        pos_list.append(level_arr)
    #init first tile / the thumbnail to be just t
    pos_list[0][0,0]='t';
    next_level=0
    for level in range(num_level-1):
        current_arr=pos_list[level]
        next_level=level+1
        next_arr=pos_list[next_level]
        
        for x in range(2**level):
            for y in range(2**level):
                #calculate top corner of next arr
                x_next=x*2
                y_next=y*2
                for ix in range(2):
                    for iy in range(2):
                        #print np.core.defchararray.add(current_arr[y,x],base[iy,ix])
                        next_arr[y_next+iy,x_next+ix]=np.core.defchararray.add(current_arr[y,x],base[iy,ix])
                        #next_arr[y_next+iy,x_next+ix]='ww'
                        #print  next_arr[y_next+iy,x_next+ix]
                        
        #print" level %d array"%(next_level)        
        #print next_arr
    data[ATLAS_ARR]=pos_list
    return data
def girder_init(host,image_id):
    image_summary_url="%sapi/v1/item/%s/tiles"%(host,image_id);
    image_summary_req=requests.get(image_summary_url)
    total_tiles=0
    num_levels=-1
    data={}
    num_x_tiles=0
    num_y_tiles=0
    if image_summary_req.status_code == requests.codes.ok:
        try:
            img_data=image_summary_req.json() 
          
            data[NUM_X_TILES]=math.ceil(img_data["sizeX"]/img_data["tileWidth"])
            data[NUM_Y_TILES]=math.ceil(img_data["sizeY"]/img_data["tileHeight"])
            data[URL]="{host_name}api/v1/item/{img_num}/tiles/zxy/%d/%d/%d".format(host_name=host,img_num=image_id)
            data[NUM_LEVELS]=img_data["levels"]
        except ValueError :
            print" Error parsing image summary data from the following request \n %s"%(image_summary_url)
            sys.exit()
    else:
            print"Could not recieve meta data using the following request\n %s"%(image_summary_url)
            sys.exit()

    
    return data


def girder_request(data,z,x,y):
     #calc range of actual tiles
    x_range=int(math.ceil(data[NUM_X_TILES]/2**((data[NUM_LEVELS]-1)-z)))
    y_range=int(math.ceil(data[NUM_Y_TILES]/2**((data[NUM_LEVELS]-1)-z)))
    
    if x>=x_range or y>=y_range:
        return -1                 
    tile_req=requests.get(data[URL]%(z,x,y))
    elapsed_time=tile_req.elapsed.total_seconds()
                    
    if tile_req.status_code == requests.codes.ok:
                       
        return elapsed_time
                        
    elif tile_req.status_code==404  :
        print " 404 error to get tile from layer %d x %d y %d error code %d"%(z,x,y,tile_req.status_code)
        return -1
                 
    elif tile_req.status_code!=404  :
        print " error to get tile from layer %d x %d y %d error code %d"%(z,x,y,tile_req.status_code)
        return -1  
    
def atlas_request(data,z,x,y):
    #print data[URL]%(data[ATLAS_ARR][z][y,x])
    tile_req=requests.get(data[URL]%(data[ATLAS_ARR][z][y,x]))
    elapsed_time=tile_req.elapsed.total_seconds()
                    
    if tile_req.status_code == requests.codes.ok:
        #print elapsed_time            
        return elapsed_time
    elif tile_req.status_code==404:
        return -1                  
                 
    elif tile_req.status_code!=404  :
        print " error to get tile from layer %d x %d y %d error code %d"%(z,x,y,tile_req.status_code)
        return -1  
    
def adrc_request(data,z,x,y):
    #levels are offset by 8
    tile_req=requests.get(data[URL]%(z+8,x,y))
    elapsed_time=tile_req.elapsed.total_seconds()
                    
    if tile_req.status_code == requests.codes.ok:
                       
        return elapsed_time
                        
    else:
        tile_req.status_code==404 
       
        return -1
                 
   
    
              
def plot_data_and_save(data):
    #plot histogram
    fig = plt.figure() 
    ax = fig.add_subplot(1,1,1)  
    time_list=[]
    data_file_name=''
    overall_max=0
    for host in data.keys():
        elapsed_time=data[host][-1]
        overall_max=max(overall_max,np.amax(elapsed_time))

    for host in data.keys():
        elapsed_time=data[host][-1]
        time_list.append(elapsed_time)
        if(host=='adrc' or host=='atlas'):
            data_file_name="elapsed_time %s"%(host)
        else:
            data_file_name="girder"
        print data_file_name
        print elapsed_time.shape
        #print elapsed_time        
        np.savetxt(data_file_name,elapsed_time)
        max_val=np.amax(elapsed_time)
        mean_val=np.mean(elapsed_time)
        print "host %s mean %f max val %f"%(host,max_val,mean_val)

        interval=np.arange(0,1,.05).tolist()
        interval.append(overall_max)
                   
        num ,bins,patch=ax.hist(elapsed_time ,interval,alpha=.5, label=host)
        ax.set_xticks(bins)                                                       
                                              
      
        ax.grid(which='both')
         
        print num        
        print bins 
    legend = ax.legend(loc='upper center', shadow=True)
    plt.xlabel('Time to recieve tile in seconds')
    plt.ylabel('Frequency')
    plt.title('Elapsed time to recieve tiles ')
                                                

    
    plt.show()


if __name__ =="__main__" :

    main();
