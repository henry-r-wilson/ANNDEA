#This script connects hits in the data to produce tracks
#Tracking Module of the ANNDEA package
#Made by Filips Fedotovs

########################################    Import libraries    #############################################
import csv
csv_reader=open('../config',"r")
config = list(csv.reader(csv_reader))
for c in config:
    if c[0]=='AFS_DIR':
        AFS_DIR=c[1]
    if c[0]=='EOS_DIR':
        EOS_DIR=c[1]
    if c[0]=='PY_DIR':
        PY_DIR=c[1]
csv_reader.close()
import sys
if PY_DIR!='': #Temp solution - the decision was made to move all libraries to EOS drive as AFS get locked during heavy HTCondor submission loads
    sys.path=['',PY_DIR]
    sys.path.append('/usr/lib64/python36.zip')
    sys.path.append('/usr/lib64/python3.6')
    sys.path.append('/usr/lib64/python3.6/lib-dynload')
    sys.path.append('/usr/lib64/python3.6/site-packages')
    sys.path.append('/usr/lib/python3.6/site-packages')
sys.path.append(AFS_DIR+'/Code/Utilities')
import UtilityFunctions as UF #This is where we keep routine utility functions
import Parameters as PM #This is where we keep framework global parameters
import pandas as pd #We use Panda for a routine data processing
pd.options.mode.chained_assignment = None #Silence annoying warnings
import math #We use it for data manipulation
import numpy as np
import os
import time
from alive_progress import alive_bar
import argparse
import ast

class bcolors:   #We use it for the interface
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

print('                                                                                                                                    ')
print('                                                                                                                                    ')
print(bcolors.HEADER+"########################################################################################################"+bcolors.ENDC)
print(bcolors.HEADER+"#########     Initialising ANNDEA Track Union Training Sample Generation module          ###############"+bcolors.ENDC)
print(bcolors.HEADER+"#########################              Written by Filips Fedotovs              #########################"+bcolors.ENDC)
print(bcolors.HEADER+"#########################                 PhD Student at UCL                   #########################"+bcolors.ENDC)
print(bcolors.HEADER+"########################################################################################################"+bcolors.ENDC)

#Setting the parser - this script is usually not run directly, but is used by a Master version Counterpart that passes the required arguments
parser = argparse.ArgumentParser(description='This script prepares training data for training the tracking model')
parser.add_argument('--SubPause',help="How long to wait in minutes after submitting 10000 jobs?", default='60')
parser.add_argument('--SubGap',help="How long to wait in minutes after submitting 10000 jobs?", default='10000')
parser.add_argument('--LocalSub',help="Local submission?", default='N')
parser.add_argument('--ForceStatus',help="Would you like the program run from specific status number? (Only for advance users)", default='0')
parser.add_argument('--RequestExtCPU',help="Would you like to request extra CPUs?", default='N')
parser.add_argument('--JobFlavour',help="Specifying the length of the HTCondor job walltime. Currently at 'workday' which is 8 hours.", default='workday')
parser.add_argument('--TrackID',help="What track name is used?", default='ANN_Track_ID')
parser.add_argument('--BrickID',help="What brick ID name is used?", default='ANN_Brick_ID')

parser.add_argument('--Mode', help='Script will continue from the last checkpoint, unless you want to start from the scratch, then type "Reset"',default='')
parser.add_argument('--ModelName',help="What  models would you like to use?", default="[]")
parser.add_argument('--Patience',help="How many checks to do before resubmitting the job?", default='15')
parser.add_argument('--RecBatchID',help="Give this training sample batch an ID", default='SHIP_UR_v1')
parser.add_argument('--f',help="Please enter the full path to the file with track reconstruction", default='/afs/cern.ch/work/f/ffedship/public/SHIP/Source_Data/SHIP_Emulsion_Rec_Raw_UR.csv')
parser.add_argument('--Xmin',help="This option restricts data to only those events that have tracks with hits x-coordinates that are above this value", default='0')
parser.add_argument('--Xmax',help="This option restricts data to only those events that have tracks with hits x-coordinates that are below this value", default='0')
parser.add_argument('--Ymin',help="This option restricts data to only those events that have tracks with hits y-coordinates that are above this value", default='0')
parser.add_argument('--Ymax',help="This option restricts data to only those events that have tracks with hits y-coordinates that are below this value", default='0')
parser.add_argument('--Log',help="Would you like to log the performance of this reconstruction? (Only available with MC data)", default='N')
parser.add_argument('--Acceptance',help="What is the ANN fit acceptance?", default='0.5')

######################################## Parsing argument values  #############################################################
args = parser.parse_args()
Mode=args.Mode.upper()
RecBatchID=args.RecBatchID
Patience=int(args.Patience)
TrackID=args.TrackID
BrickID=args.BrickID
SubPause=int(args.SubPause)*60
SubGap=int(args.SubGap)
LocalSub=(args.LocalSub=='Y')
if LocalSub:
   time_int=0
else:
    time_int=10
JobFlavour=args.JobFlavour
RequestExtCPU=(args.RequestExtCPU=='Y')
Xmin,Xmax,Ymin,Ymax=float(args.Xmin),float(args.Xmax),float(args.Ymin),float(args.Ymax)
SliceData=max(Xmin,Xmax,Ymin,Ymax)>0 #We don't slice data if all values are set to zero simultaneousy (which is the default setting)
ModelName=ast.literal_eval(args.ModelName)

Patience=int(args.Patience)
Acceptance=float(args.Acceptance)
input_file_location=args.f

Log=args.Log=='Y'
Xmin,Xmax,Ymin,Ymax=float(args.Xmin),float(args.Xmax),float(args.Ymin),float(args.Ymax)
SliceData=max(Xmin,Xmax,Ymin,Ymax)>0 #We don't slice data if all values are set to zero simultaneousy (which is the default setting)

#Establishing paths
EOSsubDIR=EOS_DIR+'/'+'ANNDEA'
EOSsubModelDIR=EOSsubDIR+'/'+'Models'
EOSsubModelMetaDIR=EOSsubDIR+'/'+'Models/'+ModelName[0]+'_Meta'
RecOutputMeta=EOS_DIR+'/ANNDEA/Data/REC_SET/'+RecBatchID+'_info.pkl'
required_file_location=EOS_DIR+'/ANNDEA/Data/REC_SET/RUTr1_'+RecBatchID+'_TRACK_SEGMENTS.csv'
required_eval_file_location=EOS_DIR+'/ANNDEA/Data/TEST_SET/EUTr1_'+RecBatchID+'_TRACK_SEGMENTS.csv'

########################################     Phase 1 - Create compact source file    #########################################
print(UF.TimeStamp(),bcolors.BOLD+'Stage 0:'+bcolors.ENDC+' Preparing the source data...')

if Log and (os.path.isfile(required_eval_file_location)==False or Mode=='RESET'):
    if os.path.isfile(EOSsubModelMetaDIR)==False:
              print(UF.TimeStamp(), bcolors.FAIL+"Fail to proceed further as the model file "+EOSsubModelMetaDIR+ " has not been found..."+bcolors.ENDC)
              exit()
    else:
           print(UF.TimeStamp(),'Loading previously saved data from ',bcolors.OKBLUE+EOSsubModelMetaDIR+bcolors.ENDC)
           MetaInput=UF.PickleOperations(EOSsubModelMetaDIR,'r', 'N/A')
           Meta=MetaInput[0]
           MinHitsTrack=Meta.MinHitsTrack
    print(UF.TimeStamp(),'Loading raw data from',bcolors.OKBLUE+input_file_location+bcolors.ENDC)
    data=pd.read_csv(input_file_location,
                header=0,
                usecols=[TrackID,BrickID,PM.x,PM.y,PM.z,PM.tx,PM.ty,PM.MC_Track_ID,PM.MC_Event_ID])

    total_rows=len(data)
    print(UF.TimeStamp(),'The raw data has ',total_rows,' hits')
    print(UF.TimeStamp(),'Removing unreconstructed hits...')
    data=data.dropna()
    final_rows=len(data)
    print(UF.TimeStamp(),'The cleaned data has ',final_rows,' hits')
    data[PM.MC_Event_ID] = data[PM.MC_Event_ID].astype(str)
    data[PM.MC_Track_ID] = data[PM.MC_Track_ID].astype(str)


    data[BrickID] = data[BrickID].astype(str)
    data[TrackID] = data[TrackID].astype(str)

    data['Rec_Seg_ID'] = data[TrackID] + '-' + data[BrickID]
    data['MC_Mother_Track_ID'] = data[PM.MC_Event_ID] + '-' + data[PM.MC_Track_ID]
    data=data.drop([TrackID],axis=1)
    data=data.drop([BrickID],axis=1)
    data=data.drop([PM.MC_Event_ID],axis=1)
    data=data.drop([PM.MC_Track_ID],axis=1)
    compress_data=data.drop([PM.x,PM.y,PM.z,PM.tx,PM.ty],axis=1)
    compress_data['MC_Mother_Track_No']= compress_data['MC_Mother_Track_ID']
    compress_data=compress_data.groupby(by=['Rec_Seg_ID','MC_Mother_Track_ID'])['MC_Mother_Track_No'].count().reset_index()
    compress_data=compress_data.sort_values(['Rec_Seg_ID','MC_Mother_Track_No'],ascending=[1,0])
    compress_data.drop_duplicates(subset='Rec_Seg_ID',keep='first',inplace=True)
    data=data.drop(['MC_Mother_Track_ID'],axis=1)
    compress_data=compress_data.drop(['MC_Mother_Track_No'],axis=1)
    data=pd.merge(data, compress_data, how="left", on=['Rec_Seg_ID'])
    if SliceData:
         print(UF.TimeStamp(),'Slicing the data...')
         ValidEvents=data.drop(data.index[(data[PM.x] > Xmax) | (data[PM.x] < Xmin) | (data[PM.y] > Ymax) | (data[PM.y] < Ymin)])
         ValidEvents.drop([PM.x,PM.y,PM.z,PM.tx,PM.ty,'MC_Mother_Track_ID'],axis=1,inplace=True)
         ValidEvents.drop_duplicates(subset='Rec_Seg_ID',keep='first',inplace=True)
         data=pd.merge(data, ValidEvents, how="inner", on=['Rec_Seg_ID'])
         final_rows=len(data.axes[0])
         print(UF.TimeStamp(),'The sliced data has ',final_rows,' hits')
    print(UF.TimeStamp(),'Removing tracks which have less than',MinHitsTrack,'hits...')
    track_no_data=data.groupby(['MC_Mother_Track_ID','Rec_Seg_ID'],as_index=False).count()
    track_no_data=track_no_data.drop([PM.y,PM.z,PM.tx,PM.ty],axis=1)
    track_no_data=track_no_data.rename(columns={PM.x: "Rec_Seg_No"})
    new_combined_data=pd.merge(data, track_no_data, how="left", on=['Rec_Seg_ID','MC_Mother_Track_ID'])
    new_combined_data = new_combined_data[new_combined_data.Rec_Seg_No >= MinHitsTrack]
    new_combined_data = new_combined_data.drop(["Rec_Seg_No"],axis=1)
    new_combined_data=new_combined_data.sort_values(['Rec_Seg_ID',PM.x],ascending=[1,1])
    grand_final_rows=len(new_combined_data)
    print(UF.TimeStamp(),'The cleaned data has ',grand_final_rows,' hits')
    new_combined_data=new_combined_data.rename(columns={PM.x: "x"})
    new_combined_data=new_combined_data.rename(columns={PM.y: "y"})
    new_combined_data=new_combined_data.rename(columns={PM.z: "z"})
    new_combined_data=new_combined_data.rename(columns={PM.tx: "tx"})
    new_combined_data=new_combined_data.rename(columns={PM.ty: "ty"})
    new_combined_data.to_csv(required_eval_file_location,index=False)
    print(bcolors.HEADER+"########################################################################################################"+bcolors.ENDC)
    print(UF.TimeStamp(), bcolors.OKGREEN+"The track segment data has been created successfully and written to"+bcolors.ENDC, bcolors.OKBLUE+required_eval_file_location+bcolors.ENDC)
    print(bcolors.HEADER+"############################################# End of the program ################################################"+bcolors.ENDC)

if os.path.isfile(required_file_location)==False or Mode=='RESET':
        if os.path.isfile(EOSsubModelMetaDIR)==False:
              print(UF.TimeStamp(), bcolors.FAIL+"Fail to proceed further as the model file "+EOSsubModelMetaDIR+ " has not been found..."+bcolors.ENDC)
              exit()
        else:
           print(UF.TimeStamp(),'Loading previously saved data from ',bcolors.OKBLUE+EOSsubModelMetaDIR+bcolors.ENDC)
           MetaInput=UF.PickleOperations(EOSsubModelMetaDIR,'r', 'N/A')
           Meta=MetaInput[0]
           MaxSLG=Meta.MaxSLG
           MaxSTG=Meta.MaxSTG
           MaxDOCA=Meta.MaxDOCA
           MaxAngle=Meta.MaxAngle
           MaxSegments=PM.MaxSegments
           MaxSeeds=PM.MaxSeeds
           VetoMotherTrack=PM.VetoMotherTrack
           MinHitsTrack=Meta.MinHitsTrack
        print(UF.TimeStamp(),'Loading raw data from',bcolors.OKBLUE+input_file_location+bcolors.ENDC)
        data=pd.read_csv(input_file_location,
                    header=0,
                    usecols=[TrackID,BrickID,PM.x,PM.y,PM.z,PM.tx,PM.ty])
        total_rows=len(data.axes[0])
        print(UF.TimeStamp(),'The raw data has ',total_rows,' hits')
        print(UF.TimeStamp(),'Removing unreconstructed hits...')
        data=data.dropna()
        final_rows=len(data.axes[0])
        print(UF.TimeStamp(),'The cleaned data has ',final_rows,' hits')
        data[BrickID] = data[BrickID].astype(str)
        data[TrackID] = data[TrackID].astype(str)

        data['Rec_Seg_ID'] = data[TrackID] + '-' + data[BrickID]
        data=data.drop([TrackID],axis=1)
        data=data.drop([BrickID],axis=1)
        if SliceData:
             print(UF.TimeStamp(),'Slicing the data...')
             ValidEvents=data.drop(data.index[(data[PM.x] > Xmax) | (data[PM.x] < Xmin) | (data[PM.y] > Ymax) | (data[PM.y] < Ymin)])
             ValidEvents.drop([PM.x,PM.y,PM.z,PM.tx,PM.ty],axis=1,inplace=True)
             ValidEvents.drop_duplicates(subset="Rec_Seg_ID",keep='first',inplace=True)
             data=pd.merge(data, ValidEvents, how="inner", on=['Rec_Seg_ID'])
             final_rows=len(data.axes[0])
             print(UF.TimeStamp(),'The sliced data has ',final_rows,' hits')
        print(UF.TimeStamp(),'Removing tracks which have less than',MinHitsTrack,'hits...')
        track_no_data=data.groupby(['Rec_Seg_ID'],as_index=False).count()
        track_no_data=track_no_data.drop([PM.y,PM.z,PM.tx,PM.ty],axis=1)
        track_no_data=track_no_data.rename(columns={PM.x: "Track_No"})
        new_combined_data=pd.merge(data, track_no_data, how="left", on=["Rec_Seg_ID"])
        new_combined_data = new_combined_data[new_combined_data.Track_No >= MinHitsTrack]
        new_combined_data = new_combined_data.drop(['Track_No'],axis=1)
        new_combined_data=new_combined_data.sort_values(['Rec_Seg_ID',PM.x],ascending=[1,1])
        grand_final_rows=len(new_combined_data.axes[0])
        print(UF.TimeStamp(),'The cleaned data has ',grand_final_rows,' hits')
        new_combined_data=new_combined_data.rename(columns={PM.x: "x"})
        new_combined_data=new_combined_data.rename(columns={PM.y: "y"})
        new_combined_data=new_combined_data.rename(columns={PM.z: "z"})
        new_combined_data=new_combined_data.rename(columns={PM.tx: "tx"})
        new_combined_data=new_combined_data.rename(columns={PM.ty: "ty"})
        new_combined_data.to_csv(required_file_location,index=False)
        data=new_combined_data[['Rec_Seg_ID','z']]
        print(UF.TimeStamp(),'Analysing the data sample in order to understand how many jobs to submit to HTCondor... ',bcolors.ENDC)
        data = data.groupby('Rec_Seg_ID')['z'].min()  #Keeping only starting hits for the each track record (we do not require the full information about track in this script)
        data=data.reset_index()
        data = data.groupby('z')['Rec_Seg_ID'].count()  #Keeping only starting hits for the each track record (we do not require the full information about track in this script)
        data=data.reset_index()
        data=data.sort_values(['z'],ascending=True)
        data['Sub_Sets']=np.ceil(data['Rec_Seg_ID']/PM.MaxSegments)
        data['Sub_Sets'] = data['Sub_Sets'].astype(int)
        data = data.values.tolist()
        print(UF.TimeStamp(), bcolors.OKGREEN+"The track segment data has been created successfully and written to"+bcolors.ENDC, bcolors.OKBLUE+required_file_location+bcolors.ENDC)
        Meta=UF.TrainingSampleMeta(RecBatchID)
        Meta.IniTrackSeedMetaData(MaxSLG,MaxSTG,MaxDOCA,MaxAngle,data,MaxSegments,VetoMotherTrack,MaxSeeds,MinHitsTrack)
        if Log:
            Meta.UpdateStatus(-2)
        else:
            Meta.UpdateStatus(1)
        print(UF.PickleOperations(RecOutputMeta,'w', Meta)[1])
        print(bcolors.HEADER+"########################################################################################################"+bcolors.ENDC)
        print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 0 has successfully completed'+bcolors.ENDC)
elif os.path.isfile(RecOutputMeta)==True:
    print(UF.TimeStamp(),'Loading previously saved data from ',bcolors.OKBLUE+RecOutputMeta+bcolors.ENDC)
    MetaInput=UF.PickleOperations(RecOutputMeta,'r', 'N/A')
    Meta=MetaInput[0]
MaxSLG=Meta.MaxSLG
MaxSTG=Meta.MaxSTG
MaxDOCA=Meta.MaxDOCA
MaxAngle=Meta.MaxAngle
JobSets=Meta.JobSets
MaxSegments=Meta.MaxSegments
MaxSeeds=Meta.MaxSeeds
VetoMotherTrack=Meta.VetoMotherTrack
MinHitsTrack=Meta.MinHitsTrack
TotJobs=0

exit()

for j in range(0,len(JobSets)):
          for sj in range(0,int(JobSets[j][2])):
              TotJobs+=1
#The function bellow helps to monitor the HTCondor jobs and keep the submission flow
def AutoPilot(wait_min, interval_min, max_interval_tolerance,program):
     print(UF.TimeStamp(),'Going on an autopilot mode for ',wait_min, 'minutes while checking HTCondor every',interval_min,'min',bcolors.ENDC)
     wait_sec=wait_min*60
     interval_sec=interval_min*60
     intervals=int(math.ceil(wait_sec/interval_sec))
     for interval in range(1,intervals+1):
         time.sleep(interval_sec)
         print(UF.TimeStamp(),"Scheduled job checkup...") #Progress display
         bad_pop=UF.CreateCondorJobs(program[1][0],
                                    program[1][1],
                                    program[1][2],
                                    program[1][3],
                                    program[1][4],
                                    program[1][5],
                                    program[1][6],
                                    program[1][7],
                                    program[1][8],
                                    program[2],
                                    program[3],
                                    program[1][9],
                                    False)
         if len(bad_pop)>0:
               print(UF.TimeStamp(),bcolors.WARNING+'Autopilot status update: There are still', len(bad_pop), 'HTCondor jobs remaining'+bcolors.ENDC)
               if interval%max_interval_tolerance==0:
                  for bp in bad_pop:
                      UF.SubmitJobs2Condor(bp,program[5],RequestExtCPU,JobFlavour)
                  print(UF.TimeStamp(), bcolors.OKGREEN+"All jobs have been resubmitted"+bcolors.ENDC)
         else:
              return True,False
     return False,False
#The function bellow helps to automate the submission process
def StandardProcess(program,status,freshstart):
        print(bcolors.HEADER+"#############################################################################################"+bcolors.ENDC)
        print(UF.TimeStamp(),bcolors.BOLD+'Stage '+str(status)+':'+bcolors.ENDC+str(program[status][0]))
        batch_sub=program[status][4]>1
        bad_pop=UF.CreateCondorJobs(program[status][1][0],
                                    program[status][1][1],
                                    program[status][1][2],
                                    program[status][1][3],
                                    program[status][1][4],
                                    program[status][1][5],
                                    program[status][1][6],
                                    program[status][1][7],
                                    program[status][1][8],
                                    program[status][2],
                                    program[status][3],
                                    program[status][1][9],
                                    False)
        if len(bad_pop)==0:
             print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+' has successfully completed'+bcolors.ENDC)
             return True,False


        elif (program[status][4])==len(bad_pop):
                 bad_pop=UF.CreateCondorJobs(program[status][1][0],
                                    program[status][1][1],
                                    program[status][1][2],
                                    program[status][1][3],
                                    program[status][1][4],
                                    program[status][1][5],
                                    program[status][1][6],
                                    program[status][1][7],
                                    program[status][1][8],
                                    program[status][2],
                                    program[status][3],
                                    program[status][1][9],
                                    batch_sub)
                 print(UF.TimeStamp(),'Submitting jobs to HTCondor... ',bcolors.ENDC)
                 _cnt=0
                 for bp in bad_pop:
                          if _cnt>SubGap:
                              print(UF.TimeStamp(),'Pausing submissions for  ',str(int(SubPause/60)), 'minutes to relieve congestion...',bcolors.ENDC)
                              time.sleep(SubPause)
                              _cnt=0
                          UF.SubmitJobs2Condor(bp,program[status][5],RequestExtCPU,JobFlavour)
                          _cnt+=bp[6]
                 if program[status][5]:
                    print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+' has successfully completed'+bcolors.ENDC)
                    return True,False
                 elif AutoPilot(600,time_int,Patience,program[status]):
                        print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+' has successfully completed'+bcolors.ENDC)
                        return True,False
                 else:
                        print(UF.TimeStamp(),bcolors.FAIL+'Stage '+str(status)+' is uncompleted...'+bcolors.ENDC)
                        return False,False


        elif len(bad_pop)>0:
            if freshstart:
                   print(UF.TimeStamp(),bcolors.WARNING+'Warning, there are still', len(bad_pop), 'HTCondor jobs remaining'+bcolors.ENDC)
                   print(bcolors.BOLD+'If you would like to wait and exit please enter E'+bcolors.ENDC)
                   print(bcolors.BOLD+'If you would like to wait please enter enter the maximum wait time in minutes'+bcolors.ENDC)
                   print(bcolors.BOLD+'If you would like to resubmit please enter R'+bcolors.ENDC)
                   UserAnswer=input(bcolors.BOLD+"Please, enter your option\n"+bcolors.ENDC)
                   if UserAnswer=='E':
                       print(UF.TimeStamp(),'OK, exiting now then')
                       exit()
                   if UserAnswer=='R':
                      _cnt=0
                      for bp in bad_pop:
                           if _cnt>SubGap:
                              print(UF.TimeStamp(),'Pausing submissions for  ',str(int(SubPause/60)), 'minutes to relieve congestion...',bcolors.ENDC)
                              time.sleep(SubPause)
                              _cnt=0
                           UF.SubmitJobs2Condor(bp,program[status][5],RequestExtCPU,JobFlavour)
                           _cnt+=bp[6]
                      print(UF.TimeStamp(), bcolors.OKGREEN+"All jobs have been resubmitted"+bcolors.ENDC)
                      if program[status][5]:
                          print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+' has successfully completed'+bcolors.ENDC)
                          return True,False
                      elif AutoPilot(600,time_int,Patience,program[status]):
                          print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+ 'has successfully completed'+bcolors.ENDC)
                          return True,False
                      else:
                          print(UF.TimeStamp(),bcolors.FAIL+'Stage '+str(status)+' is uncompleted...'+bcolors.ENDC)
                          return False,False
                   else:
                      if program[status][5]:
                          print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+' has successfully completed'+bcolors.ENDC)
                          return True,False
                      elif AutoPilot(int(UserAnswer),time_int,Patience,program[status]):
                          print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+ 'has successfully completed'+bcolors.ENDC)
                          return True,False
                      else:
                          print(UF.TimeStamp(),bcolors.FAIL+'Stage '+str(status)+' is uncompleted...'+bcolors.ENDC)
                          return False,False
            else:
                      _cnt=0
                      for bp in bad_pop:
                           if _cnt>SubGap:
                              print(UF.TimeStamp(),'Pausing submissions for  ',str(int(SubPause/60)), 'minutes to relieve congestion...',bcolors.ENDC)
                              time.sleep(SubPause)
                              _cnt=0
                           UF.SubmitJobs2Condor(bp,program[status][5],RequestExtCPU,JobFlavour)
                           _cnt+=bp[6]
                      if program[status][5]:
                           print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+' has successfully completed'+bcolors.ENDC)
                           return True,False
                      elif AutoPilot(600,time_int,Patience,program[status]):
                           print(UF.TimeStamp(),bcolors.OKGREEN+'Stage '+str(status)+ 'has successfully completed'+bcolors.ENDC)
                           return True,False
                      else:
                          print(UF.TimeStamp(),bcolors.FAIL+'Stage '+str(status)+' is uncompleted...'+bcolors.ENDC)
                          return False,False

#If we chose reset mode we do a full cleanup.
# #Reconstructing a single brick can cause in gereation of 100s of thousands of files - need to make sure that we remove them.
if Mode=='RESET':
    print(UF.TimeStamp(),'Performing the cleanup... ',bcolors.ENDC)
    HTCondorTag="SoftUsed == \"ANNDEA-RTr1a-"+RecBatchID+"\""
    UF.RecCleanUp(AFS_DIR, EOS_DIR, 'RTr1_'+RecBatchID, ['RTr1a','RTr1b','RTr1c','RTr1d',RecBatchID+'_RTr_OUTPUT_CLEANED.csv'], HTCondorTag)
    FreshStart=False
if Mode=='CLEANUP':
    Status=5
else:
    Status=int(args.ForceStatus)
################ Set the execution sequence for the script
###### Stage 0
prog_entry=[]
job_sets=[]
for i in range(0,Xsteps):
                job_sets.append(Ysteps)
prog_entry.append(' Sending hit cluster to the HTCondor, so the model assigns weights between hits')
prog_entry.append([AFS_DIR,EOS_DIR,PY_DIR,'/ANNDEA/Data/REC_SET/','hit_cluster_rec_set','RTr1a','.csv',RecBatchID,job_sets,'RTr1a_ReconstructTracks_Sub.py'])
prog_entry.append([' --stepZ ', ' --stepY ', ' --stepX ', " --zOffset ", " --yOffset ", " --xOffset ", ' --cut_dt ', ' --cut_dr ', ' --ModelName ',' --Z_overlap ',' --Y_overlap ',' --X_overlap ', ' --Z_ID_Max ', ' --CheckPoint '])
prog_entry.append([stepZ,stepY,stepX,z_offset, y_offset, x_offset, cut_dt,cut_dr, ModelName,Z_overlap,Y_overlap,X_overlap, Zsteps, args.CheckPoint])
prog_entry.append(Xsteps*Ysteps)
prog_entry.append(LocalSub)
Program.append(prog_entry)

if Mode=='RESET':
   print(UF.TimeStamp(),UF.ManageTempFolders(prog_entry,'Delete'))
#Setting up folders for the output. The reconstruction of just one brick can easily generate >100k of files. Keeping all that blob in one directory can cause problems on lxplus.
print(UF.TimeStamp(),UF.ManageTempFolders(prog_entry,'Create'))

###### Stage 1
prog_entry=[]
job_sets=Xsteps
prog_entry.append(' Sending hit cluster to the HTCondor, so the reconstructed clusters can be merged along y-axis')
prog_entry.append([AFS_DIR,EOS_DIR,PY_DIR,'/ANNDEA/Data/REC_SET/','hit_cluster_rec_y_set','RTr1b','.csv',RecBatchID,job_sets,'RTr1b_LinkSegmentsY_Sub.py'])
prog_entry.append([' --Y_ID_Max ', ' --i '])
prog_entry.append([Ysteps,Xsteps])
prog_entry.append(Xsteps)
prog_entry.append(LocalSub)
Program.append(prog_entry)
if Mode=='RESET':
   print(UF.TimeStamp(),UF.ManageTempFolders(prog_entry,'Delete'))
#Setting up folders for the output. The reconstruction of just one brick can easily generate >100k of files. Keeping all that blob in one directory can cause problems on lxplus.
print(UF.TimeStamp(),UF.ManageTempFolders(prog_entry,'Create'))

###### Stage 2
prog_entry=[]
job_sets=1
prog_entry.append(' Sending hit cluster to the HTCondor, so the reconstructed clusters can be merged along x-axis')
prog_entry.append([AFS_DIR,EOS_DIR,PY_DIR,'/ANNDEA/Data/REC_SET/','hit_cluster_rec_x_set','RTr1c','.csv',RecBatchID,job_sets,'RTr1c_LinkSegmentsX_Sub.py'])
prog_entry.append([' --X_ID_Max '])
prog_entry.append([Xsteps])
prog_entry.append(1)
prog_entry.append(True) #This part we can execute locally, no need for HTCondor
Program.append(prog_entry)
if Mode=='RESET':
   print(UF.TimeStamp(),UF.ManageTempFolders(prog_entry,'Delete'))
#Setting up folders for the output. The reconstruction of just one brick can easily generate >100k of files. Keeping all that blob in one directory can cause problems on lxplus.
print(UF.TimeStamp(),UF.ManageTempFolders(prog_entry,'Create'))

###### Stage 3
Program.append('Custom')


print(UF.TimeStamp(),'There are '+str(len(Program)+1)+' stages (0-'+str(len(Program)+1)+') of this script',bcolors.ENDC)
print(UF.TimeStamp(),'Current stage has a code',Status,bcolors.ENDC)
while Status<len(Program):
    if Program[Status]!='Custom':
        #Standard process here
        Result=StandardProcess(Program,Status,FreshStart)
        if Result[0]:
            FreshStart=Result[1]
            if int(args.ForceStatus)==0:
                Status+=1
                continue
            else:
                exit()
        else:
            Status=len(Program)+1
            break

    elif Status==3:
       #Non standard processes (that don't follow the general pattern) have been coded here
       print(bcolors.HEADER+"#############################################################################################"+bcolors.ENDC)
       print(UF.TimeStamp(),bcolors.BOLD+'Stage 3:'+bcolors.ENDC+' Using the results from previous steps to map merged trackIDs to the original reconstruction file')
       try:
            #Read the output with hit- ANN Track map
            FirstFile=EOS_DIR+'/ANNDEA/Data/REC_SET/Temp_RTr1c_'+RecBatchID+'_0'+'/RTr1c_'+RecBatchID+'_hit_cluster_rec_x_set_0.csv'
            print(UF.TimeStamp(),'Loading the file ',bcolors.OKBLUE+FirstFile+bcolors.ENDC)
            TrackMap=pd.read_csv(FirstFile,header=0)
            input_file_location=args.f
            print(UF.TimeStamp(),'Loading raw data from',bcolors.OKBLUE+input_file_location+bcolors.ENDC)
            #Reading the original file with Raw hits
            Data=pd.read_csv(input_file_location,header=0)
            Data[PM.Hit_ID] = Data[PM.Hit_ID].astype(str)

            if SliceData: #If we want to perform reconstruction on the fraction of the Brick
               CutData=Data.drop(Data.index[(Data[PM.x] > Xmax) | (Data[PM.x] < Xmin) | (Data[PM.y] > Ymax) | (Data[PM.y] < Ymin)]) #The focus area where we reconstruct
            else:
               CutData=Data #If we reconstruct the whole brick we jsut take the whole data. No need to separate.

            CutData.drop([RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID'],axis=1,inplace=True,errors='ignore') #Removing old ANNDEA reconstruction results so we can overwrite with the new ones
            #Map reconstructed ANN tracks to hits in the Raw file - this is in essesential for the final output of the tracking
            TrackMap['HitID'] = TrackMap['HitID'].astype(str)
            CutData[PM.Hit_ID] = CutData[PM.Hit_ID].astype(str)
            CutData=pd.merge(CutData,TrackMap,how='left', left_on=[PM.Hit_ID], right_on=['HitID'])

            CutData.drop(['HitID'],axis=1,inplace=True) #Make sure that HitID is not the Hit ID name in the raw data.
            Data=CutData


            #It was discovered that the output is not perfect: while the hit fidelity is achieved we don't have a full plate hit fidelity for a given track. It is still possible for a track to have multiple hits at one plate.
            #In order to fix it we need to apply some additional logic to those problematic tracks.
            print(UF.TimeStamp(),'Identifying problematic tracks where there is more than one hit per plate...')
            Hit_Map=Data[[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.x,PM.y,PM.z,PM.tx,PM.ty,PM.Hit_ID]] #Separating the hit map
            Data.drop([RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID'],axis=1,inplace=True) #Remove the ANNDEA tracking info from the main data





            Hit_Map=Hit_Map.dropna() #Remove unreconstructing hits - we are not interested in them atm
            Hit_Map_Stats=Hit_Map[[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.z,PM.Hit_ID]] #Calculating the stats

            Hit_Map_Stats=Hit_Map_Stats.groupby([RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID']).agg({PM.z:pd.Series.nunique,PM.Hit_ID: pd.Series.nunique}).reset_index() #Calculate the number fo unique plates and hits
            Ini_No_Tracks=len(Hit_Map_Stats)
            print(UF.TimeStamp(),bcolors.WARNING+'The initial number of tracks is '+ str(Ini_No_Tracks)+bcolors.ENDC)
            Hit_Map_Stats=Hit_Map_Stats.rename(columns={PM.z: "No_Plates",PM.Hit_ID:"No_Hits"}) #Renaming the columns so they don't interfere once we join it back to the hit map
            Hit_Map_Stats=Hit_Map_Stats[Hit_Map_Stats.No_Plates >= PM.MinHitsTrack]
            Prop_No_Tracks=len(Hit_Map_Stats)
            print(UF.TimeStamp(),bcolors.WARNING+'After dropping single hit tracks, left '+ str(Prop_No_Tracks)+' tracks...'+bcolors.ENDC)
            Hit_Map=pd.merge(Hit_Map,Hit_Map_Stats,how='inner',on = [RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID']) #Join back to the hit map
            Good_Tracks=Hit_Map[Hit_Map.No_Plates == Hit_Map.No_Hits] #For all good tracks the number of hits matches the number of plates, we won't touch them
            Good_Tracks=Good_Tracks[[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.Hit_ID]] #Just strip off the information that we don't need anymore

            Bad_Tracks=Hit_Map[Hit_Map.No_Plates < Hit_Map.No_Hits] #These are the bad guys. We need to remove this extra hits
            Bad_Tracks=Bad_Tracks[[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.x,PM.y,PM.z,PM.tx,PM.ty,PM.Hit_ID]]

            #Id the problematic plates
            Bad_Tracks_Stats=Bad_Tracks[[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.z,PM.Hit_ID]]
            Bad_Tracks_Stats=Bad_Tracks_Stats.groupby([RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.z]).agg({PM.Hit_ID: pd.Series.nunique}).reset_index() #Which plates have double hits?
            Bad_Tracks_Stats=Bad_Tracks_Stats.rename(columns={PM.Hit_ID: "Problem"}) #Renaming the columns so they don't interfere once we join it back to the hit map
            Bad_Tracks=pd.merge(Bad_Tracks,Bad_Tracks_Stats,how='inner',on = [RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.z])



            Bad_Tracks.sort_values([RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.z],ascending=[0,0,1],inplace=True)

            Bad_Tracks_CP_File=EOS_DIR+'/ANNDEA/Data/REC_SET/Temp_RTr1c_'+RecBatchID+'_0'+'/RTr1c_'+RecBatchID+'_Bad_Tracks_CP.csv'
            if os.path.isfile(Bad_Tracks_CP_File)==False or Mode=='RESET':

                Bad_Tracks_Head=Bad_Tracks[[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID']]
                Bad_Tracks_Head.drop_duplicates(inplace=True)
                Bad_Tracks_List=Bad_Tracks.values.tolist() #I find it is much easier to deal with tracks in list format when it comes to fitting
                Bad_Tracks_Head=Bad_Tracks_Head.values.tolist()
                Bad_Track_Pool=[]

                #Bellow we build the track representatation that we can use to fit slopes
                with alive_bar(len(Bad_Tracks_Head),force_tty=True, title='Building track representations...') as bar:
                            for bth in Bad_Tracks_Head:
                               bar()
                               bth.append([])
                               bt=0
                               trigger=False
                               while bt<(len(Bad_Tracks_List)):
                                   if (bth[0]==Bad_Tracks_List[bt][0] and bth[1]==Bad_Tracks_List[bt][1]):
                                      if Bad_Tracks_List[bt][8]==1: #We only build polynomials for hits in a track that do not have duplicates - these are 'trusted hits'
                                         bth[2].append(Bad_Tracks_List[bt][2:-2])
                                      del Bad_Tracks_List[bt]
                                      bt-=1
                                      trigger=True
                                   elif trigger:
                                       break
                                   else:
                                       continue
                                   bt+=1


                with alive_bar(len(Bad_Tracks_Head),force_tty=True, title='Fitting the tracks...') as bar:
                 for bth in Bad_Tracks_Head:
                   bar()
                   if len(bth[2])==1: #Only one trusted hit - In these cases whe we take only tx and ty slopes of the single base track. Polynomial of the first degree and the equations of the line are x=ax+tx*z and y=ay+ty*z
                       x=bth[2][0][0]
                       z=bth[2][0][2]
                       tx=bth[2][0][3]
                       ax=x-tx*z
                       bth.append(ax) #Append x intercept
                       bth.append(tx) #Append x slope
                       bth.append(0) #Append a placeholder slope (for polynomial case)
                       y=bth[2][0][1]
                       ty=bth[2][0][4]
                       ay=y-ty*z
                       bth.append(ay) #Append x intercept
                       bth.append(ty) #Append x slope
                       bth.append(0) #Append a placeholder slope (for polynomial case)
                       del(bth[2])
                   elif len(bth[2])==2: #Two trusted hits - In these cases whe we fit a polynomial of the first degree and the equations of the line are x=ax+tx*z and y=ay+ty*z
                       x,y,z=[],[],[]
                       x=[bth[2][0][0],bth[2][1][0]]
                       y=[bth[2][0][1],bth[2][1][1]]
                       z=[bth[2][0][2],bth[2][1][2]]
                       tx=np.polyfit(z,x,1)[0]
                       ax=np.polyfit(z,x,1)[1]
                       ty=np.polyfit(z,y,1)[0]
                       ay=np.polyfit(z,y,1)[1]
                       bth.append(ax) #Append x intercept
                       bth.append(tx) #Append x slope
                       bth.append(0) #Append a placeholder slope (for polynomial case)
                       bth.append(ay) #Append x intercept
                       bth.append(ty) #Append x slope
                       bth.append(0) #Append a placeholder slope (for polynomial case)
                       del(bth[2])
                   elif len(bth[2])==0:
                       del(bth)
                       continue
                   else: #Three pr more trusted hits - In these cases whe we fit a polynomial of the second degree and the equations of the line are x=ax+(t1x*z)+(t2x*z*z) and y=ay+(t1y*z)+(t2y*z*z)
                       x,y,z=[],[],[]
                       for i in bth[2]:
                           x.append(i[0])
                       for j in bth[2]:
                           y.append(j[1])
                       for k in bth[2]:
                           z.append(k[2])
                       t2x=np.polyfit(z,x,2)[0]
                       t1x=np.polyfit(z,x,2)[1]
                       ax=np.polyfit(z,x,2)[2]

                       t2y=np.polyfit(z,y,2)[0]
                       t1y=np.polyfit(z,y,2)[1]
                       ay=np.polyfit(z,y,2)[2]

                       bth.append(ax) #Append x intercept
                       bth.append(t1x) #Append x slope
                       bth.append(t2x) #Append a placeholder slope (for polynomial case)
                       bth.append(ay) #Append x intercept
                       bth.append(t1y) #Append x slope
                       bth.append(t2y) #Append a placeholder slope (for polynomial case)
                       del(bth[2])


                #Once we get coefficients for all tracks we convert them back to Pandas dataframe and join back to the data
                Bad_Tracks_Head=pd.DataFrame(Bad_Tracks_Head, columns = [RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID','ax','t1x','t2x','ay','t1y','t2y'])

                print(UF.TimeStamp(),'Saving the checkpoint file ',bcolors.OKBLUE+Bad_Tracks_CP_File+bcolors.ENDC)
                Bad_Tracks_Head.to_csv(Bad_Tracks_CP_File,index=False)
            else:
               print(UF.TimeStamp(),'Loadingthe checkpoint file ',bcolors.OKBLUE+Bad_Tracks_CP_File+bcolors.ENDC)
               Bad_Tracks_Head=pd.read_csv(Bad_Tracks_CP_File,header=0)
               Bad_Tracks_Head=Bad_Tracks_Head[Bad_Tracks_Head.ax != '[]']
               Bad_Tracks_Head['ax'] = Bad_Tracks_Head['ax'].astype(float)
               Bad_Tracks_Head['ay'] = Bad_Tracks_Head['ay'].astype(float)
               Bad_Tracks_Head['t1x'] = Bad_Tracks_Head['t1x'].astype(float)
               Bad_Tracks_Head['t2x'] = Bad_Tracks_Head['t2x'].astype(float)
               Bad_Tracks_Head['t1y'] = Bad_Tracks_Head['t1y'].astype(float)
               Bad_Tracks_Head['t2y'] = Bad_Tracks_Head['t2y'].astype(float)

            print(UF.TimeStamp(),'Removing problematic hits...')
            Bad_Tracks=pd.merge(Bad_Tracks,Bad_Tracks_Head,how='inner',on = [RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID'])



            print(UF.TimeStamp(),'Calculating x and y coordinates of the fitted line for all plates in the track...')
            #Calculating x and y coordinates of the fitted line for all plates in the track
            Bad_Tracks['new_x']=Bad_Tracks['ax']+(Bad_Tracks[PM.z]*Bad_Tracks['t1x'])+((Bad_Tracks[PM.z]**2)*Bad_Tracks['t2x'])
            Bad_Tracks['new_y']=Bad_Tracks['ay']+(Bad_Tracks[PM.z]*Bad_Tracks['t1y'])+((Bad_Tracks[PM.z]**2)*Bad_Tracks['t2y'])

            #Calculating how far hits deviate from the fit polynomial
            print(UF.TimeStamp(),'Calculating how far hits deviate from the fit polynomial...')
            Bad_Tracks['d_x']=Bad_Tracks[PM.x]-Bad_Tracks['new_x']
            Bad_Tracks['d_y']=Bad_Tracks[PM.y]-Bad_Tracks['new_y']

            Bad_Tracks['d_r']=Bad_Tracks['d_x']**2+Bad_Tracks['d_y']**2
            Bad_Tracks['d_r'] = Bad_Tracks['d_r'].astype(float)
            Bad_Tracks['d_r']=np.sqrt(Bad_Tracks['d_r']) #Absolute distance
            Bad_Tracks=Bad_Tracks[[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.z,PM.Hit_ID,'d_r']]

            #Sort the tracks and their hits by Track ID, Plate and distance to the perfect line
            print(UF.TimeStamp(),'Sorting the tracks and their hits by Track ID, Plate and distance to the perfect line...')
            Bad_Tracks.sort_values([RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.z,'d_r'],ascending=[0,0,1,1],inplace=True)

            #If there are two hits per plate we will keep the one which is closer to the line
            Bad_Tracks.drop_duplicates(subset=[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.z],keep='first',inplace=True)
            Bad_Tracks=Bad_Tracks[[RecBatchID+'_Brick_ID',RecBatchID+'_Track_ID',PM.Hit_ID]]
            Good_Tracks=pd.concat([Good_Tracks,Bad_Tracks]) #Combine all ANNDEA tracks together

            Data=pd.merge(Data,Good_Tracks,how='left', on=[PM.Hit_ID]) #Re-map corrected ANNDEA Tracks back to the main data

            output_file_location=EOS_DIR+'/ANNDEA/Data/REC_SET/'+RecBatchID+'_RTr_OUTPUT_CLEANED.csv' #Final output. We can use this file for further operations
            Data.to_csv(output_file_location,index=False)
            print(UF.TimeStamp(), bcolors.OKGREEN+"The tracked data has been written to"+bcolors.ENDC, bcolors.OKBLUE+output_file_location+bcolors.ENDC)
            print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 4 has successfully completed'+bcolors.ENDC)
            Status=4
       except Exception as e:
          print(UF.TimeStamp(),bcolors.FAIL+'Stage 4 is uncompleted due to: '+str(e)+bcolors.ENDC)
          Status=5
          break
if Status==4:
    # Removing the temp files that were generated by the process
    print(UF.TimeStamp(),'Performing the cleanup... ',bcolors.ENDC)
    HTCondorTag="SoftUsed == \"ANNDEA-RTr1a-"+RecBatchID+"\""
    UF.RecCleanUp(AFS_DIR, EOS_DIR, 'RTr1a_'+RecBatchID, [], HTCondorTag)
    HTCondorTag="SoftUsed == \"ANNDEA-RTr1b-"+RecBatchID+"\""
    UF.RecCleanUp(AFS_DIR, EOS_DIR, 'RTr1b_'+RecBatchID, [], HTCondorTag)
    for p in Program:
        if p!='Custom':
           print(UF.TimeStamp(),UF.ManageTempFolders(p,'Delete'))
    print(UF.TimeStamp(), bcolors.OKGREEN+"Reconstruction has been completed"+bcolors.ENDC)
    exit()
else:
    print(UF.TimeStamp(), bcolors.FAIL+"Reconstruction has not been completed as one of the processes has timed out or --ForceStatus!=0 option was chosen. Please run the script again (without Reset Mode)."+bcolors.ENDC)
    exit()



