#This simple connects hits in the data to produce tracks
#Tracking Module of the ANNADEA package
#Made by Filips Fedotovs


########################################    Import libraries    #############################################
import csv
import argparse
import pandas as pd #We use Panda for a routine data processing
import math #We use it for data manipulation
import numpy as np
import os
import time
import ast
from alive_progress import alive_bar
import random
import gc
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
parser.add_argument('--Mode', help='Script will continue from the last checkpoint, unless you want to start from the scratch, then type "Reset"',default='')
parser.add_argument('--ModelName',help="WHat GNN model would you like to use?", default="['MH_GNN_5FTR_4_120_4_120']")
parser.add_argument('--Patience',help="How many checks to do before resubmitting the job?", default='15')
parser.add_argument('--TrainSampleID',help="Give this training sample batch an ID", default='SHIP_UR_v1')
parser.add_argument('--f',help="Please enter the full path to the file with track reconstruction", default='/afs/cern.ch/work/f/ffedship/public/SHIP/Source_Data/SHIP_Emulsion_FEDRA_Raw_UR.csv')
parser.add_argument('--Xmin',help="This option restricts data to only those events that have tracks with hits x-coordinates that are above this value", default='0')
parser.add_argument('--Xmax',help="This option restricts data to only those events that have tracks with hits x-coordinates that are below this value", default='0')
parser.add_argument('--Ymin',help="This option restricts data to only those events that have tracks with hits y-coordinates that are above this value", default='0')
parser.add_argument('--Ymax',help="This option restricts data to only those events that have tracks with hits y-coordinates that are below this value", default='0')
parser.add_argument('--Samples',help="How many samples? Please enter the number or ALL if you want to use all data", default='ALL')
parser.add_argument('--LabelRatio',help="What is the desired proportion of genuine seeds in the training/validation sets", default='0.5')
parser.add_argument('--TrainSampleSize',help="Maximum number of samples per Training file", default='50000')
parser.add_argument('--ClassHeaders',help="What class headers to use?", default="['EM Background']")
parser.add_argument('--ClassNames',help="What class headers to use?", default="[['Flag','ProcID']]")
parser.add_argument('--ClassValues',help="What class values to use?", default="[['13','-13'],['8']]")
######################################## Parsing argument values  #############################################################
args = parser.parse_args()
Mode=args.Mode.upper()
ModelName=ast.literal_eval(args.ModelName)
ClassHeaders=ast.literal_eval(args.ClassHeaders)
ClassNames=ast.literal_eval(args.ClassNames)
ClassValues=ast.literal_eval(args.ClassValues)

TrainSampleID=args.TrainSampleID
Patience=int(args.Patience)
TrainSampleSize=int(args.TrainSampleSize)
input_file_location=args.f
Xmin,Xmax,Ymin,Ymax=float(args.Xmin),float(args.Xmax),float(args.Ymin),float(args.Ymax)
SliceData=max(Xmin,Xmax,Ymin,Ymax)>0 #We don't slice data if all values are set to zero simultaneousy (which is the default setting)

#Loading Directory locations
csv_reader=open('../config',"r")
config = list(csv.reader(csv_reader))
for c in config:
    if c[0]=='AFS_DIR':
        AFS_DIR=c[1]
    if c[0]=='EOS_DIR':
        EOS_DIR=c[1]
csv_reader.close()
import sys
sys.path.insert(1, AFS_DIR+'/Code/Utilities/')
import UtilityFunctions as UF #This is where we keep routine utility functions
import Parameters as PM #This is where we keep framework global parameters

#Establishing paths
EOSsubDIR=EOS_DIR+'/'+'ANNADEA'
EOSsubModelDIR=EOSsubDIR+'/'+'Models'
TrainSampleOutputMeta=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/'+TrainSampleID+'_info.pkl'
required_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MCTr1_'+TrainSampleID+'_TRACKS.csv'
ColumnsToImport=[PM.Rec_Track_ID,PM.Rec_Track_Domain,PM.x,PM.y,PM.z,PM.tx,PM.ty,PM.MC_Track_ID,PM.MC_Event_ID]
ExtraColumns=[]
for i in ClassNames:
    for j in i:
        ColumnsToImport.append(j)
        if j in ExtraColumns==False:
                ExtraColumns.append(j)
########################################     Phase 1 - Create compact source file    #########################################
print(UF.TimeStamp(),bcolors.BOLD+'Stage 0:'+bcolors.ENDC+' Preparing the source data...')

if os.path.isfile(required_file_location)==False or Mode=='RESET':
        print(UF.TimeStamp(),'Loading raw data from',bcolors.OKBLUE+input_file_location+bcolors.ENDC)
        data=pd.read_csv(input_file_location,
                    header=0,
                    usecols=ColumnsToImport)
        total_rows=len(data.axes[0])
        print(UF.TimeStamp(),'The raw data has ',total_rows,' hits')
        print(UF.TimeStamp(),'Removing unreconstructed hits...')
        data=data.dropna()
        final_rows=len(data.axes[0])
        print(UF.TimeStamp(),'The cleaned data has ',final_rows,' hits')
        data[PM.MC_Event_ID] = data[PM.MC_Event_ID].astype(str)
        for i in ExtraColumns:
            data[i]=data[i].astype(str)
        data[PM.MC_Track_ID] = data[PM.MC_Track_ID].astype(str)
        data[PM.Rec_Track_ID] = data[PM.Rec_Track_ID].astype(str)
        data[PM.Rec_Track_Domain] = data[PM.Rec_Track_Domain].astype(str)
        data[PM.MC_Event_ID] = data[PM.MC_Event_ID].astype(str)
        data['Rec_Seg_ID'] = data[PM.Rec_Track_Domain] + '-' + data[PM.Rec_Track_ID]
        data['MC_Mother_Track_ID'] = data[PM.MC_Event_ID] + '-' + data[PM.MC_Track_ID]
        data=data.drop([PM.Rec_Track_ID],axis=1)
        data=data.drop([PM.Rec_Track_Domain],axis=1)
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
             ValidEvents.drop([PM.x,PM.y,PM.z,PM.tx,PM.ty,'MC_Mother_Track_ID']+ExtraColumns,axis=1,inplace=True)
             ValidEvents.drop_duplicates(subset='Rec_Seg_ID',keep='first',inplace=True)
             data=pd.merge(data, ValidEvents, how="inner", on=['Rec_Seg_ID'])
             final_rows=len(data.axes[0])
             print(UF.TimeStamp(),'The sliced data has ',final_rows,' hits')

        output_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MCTr1_'+TrainSampleID+'_TRACKS.csv'
        print(UF.TimeStamp(),'Removing tracks which have less than',PM.MinHitsTrack,'hits...')
        track_no_data=data.groupby(['MC_Mother_Track_ID','Rec_Seg_ID']+ExtraColumns,as_index=False).count()
        track_no_data=track_no_data.drop([PM.y,PM.z,PM.tx,PM.ty],axis=1)
        track_no_data=track_no_data.rename(columns={PM.x: "Rec_Seg_No"})
        new_combined_data=pd.merge(data, track_no_data, how="left", on=['Rec_Seg_ID','MC_Mother_Track_ID']+ExtraColumns)
        new_combined_data = new_combined_data[new_combined_data.Rec_Seg_No >= PM.MinHitsTrack]
        new_combined_data = new_combined_data.drop(["Rec_Seg_No"],axis=1)
        new_combined_data=new_combined_data.sort_values(['Rec_Seg_ID',PM.x],ascending=[1,1])
        grand_final_rows=len(new_combined_data.axes[0])
        print(UF.TimeStamp(),'The cleaned data has ',grand_final_rows,' hits')
        new_combined_data=new_combined_data.rename(columns={PM.x: "x"})
        new_combined_data=new_combined_data.rename(columns={PM.y: "y"})
        new_combined_data=new_combined_data.rename(columns={PM.z: "z"})
        new_combined_data=new_combined_data.rename(columns={PM.tx: "tx"})
        new_combined_data=new_combined_data.rename(columns={PM.ty: "ty"})
        new_combined_data.drop(['MC_Mother_Track_ID'],axis=1,inplace=True)
        new_combined_data.to_csv(output_file_location,index=False)
        data=new_combined_data[['Rec_Seg_ID']]
        print(UF.TimeStamp(),'Analysing the data sample in order to understand how many jobs to submit to HTCondor... ',bcolors.ENDC)
        data.drop_duplicates(subset='Rec_Seg_ID',keep='first',inplace=True)
        data = data.values.tolist()
        no_submissions=math.ceil(len(data)/PM.MaxSeeds)
        print(UF.TimeStamp(), bcolors.OKGREEN+"The track segment data has been created successfully and written to"+bcolors.ENDC, bcolors.OKBLUE+output_file_location+bcolors.ENDC)
        Meta=UF.TrainingSampleMeta(TrainSampleID)
        Meta.IniTrackMetaData(ClassHeaders,ClassNames,ClassValues,PM.MaxSegments,no_submissions)
        Meta.UpdateStatus(1)
        print(UF.PickleOperations(TrainSampleOutputMeta,'w', Meta)[1])
        print(bcolors.HEADER+"########################################################################################################"+bcolors.ENDC)
        print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 0 has successfully completed'+bcolors.ENDC)
elif os.path.isfile(TrainSampleOutputMeta)==True:
    print(UF.TimeStamp(),'Loading previously saved data from ',bcolors.OKBLUE+TrainSampleOutputMeta+bcolors.ENDC)
    MetaInput=UF.PickleOperations(TrainSampleOutputMeta,'r', 'N/A')
    Meta=MetaInput[0]
ClassHeaders=Meta.ClassHeaders
ClassNames=Meta.ClassNames
ClassValues=Meta.ClassValues
JobSets=Meta.JobSets
MaxSegments=Meta.MaxSegments
TotJobs=JobSets


########################################     Preset framework parameters    #########################################
FreshStart=True

def UpdateStatus(status):
    Meta.UpdateStatus(status)
    print(UF.PickleOperations(TrainSampleOutputMeta,'w', Meta)[1])
def AutoPilot(wait_min, interval_min, max_interval_tolerance,AFS,EOS,path,o,pfx,sfx,ID,loop_params,OptionHeader,OptionLine,Sub_File,Exception=['',''], Log=False, GPU=False):
     print(UF.TimeStamp(),'Going on an autopilot mode for ',wait_min, 'minutes while checking HTCondor every',interval_min,'min',bcolors.ENDC)
     wait_sec=wait_min*60
     interval_sec=interval_min*60
     intervals=int(math.ceil(wait_sec/interval_sec))
     for interval in range(1,intervals+1):
         time.sleep(interval_sec)
         print(UF.TimeStamp(),"Scheduled job checkup...") #Progress display
         bad_pop=UF.CreateCondorJobs(AFS,EOS,
                                    path,
                                    o,
                                    pfx,
                                    sfx,
                                    ID,
                                    loop_params,
                                    OptionHeader,
                                    OptionLine,
                                    Sub_File,
                                    False,
                                    Exception,
                                    Log,
                                    GPU)
         if len(bad_pop)>0:
               print(UF.TimeStamp(),bcolors.WARNING+'Autopilot status update: There are still', len(bad_pop), 'HTCondor jobs remaining'+bcolors.ENDC)
               if interval%max_interval_tolerance==0:
                  for bp in bad_pop:
                      UF.SubmitJobs2Condor(bp)
                  print(UF.TimeStamp(), bcolors.OKGREEN+"All jobs have been resubmitted"+bcolors.ENDC)
         else:
              return True
     return False

if Mode=='RESET':
    print(UF.TimeStamp(),'Performing the cleanup... ',bcolors.ENDC)
    HTCondorTag="SoftUsed == \"ANNADEA-MCTr1a-"+TrainSampleID+"\""
    UF.TrainCleanUp(AFS_DIR, EOS_DIR, 'MCTr1a_'+TrainSampleID, ['MCTr1a'], HTCondorTag)
    HTCondorTag="SoftUsed == \"ANNADEA-MCTr1b-"+TrainSampleID+"\""
    UF.TrainCleanUp(AFS_DIR, EOS_DIR, 'MCTr1b_'+TrainSampleID, ['MCTr1b'], HTCondorTag)
    HTCondorTag="SoftUsed == \"ANNADEA-MCTr1c-"+TrainSampleID+"\""
    UF.TrainCleanUp(AFS_DIR, EOS_DIR, 'MCTr1c_'+TrainSampleID, ['MCTr1c'], HTCondorTag)
    HTCondorTag="SoftUsed == \"ANNADEA-MCTr1d-"+TrainSampleID+"\""
    UF.TrainCleanUp(AFS_DIR, EOS_DIR, 'MCTr1d_'+TrainSampleID, ['MCTr1d'], HTCondorTag)
    FreshStart=False
    UpdateStatus(1)
    status=1
else:
    print(UF.TimeStamp(),'Analysing the current script status...',bcolors.ENDC)

    status=Meta.Status[-1]
print(UF.TimeStamp(),'There are 8 stages (0-7) of this script',status,bcolors.ENDC)
print(UF.TimeStamp(),'Current status has a stage',status,bcolors.ENDC)

while status<7:
      if status==1:
          print(bcolors.HEADER+"#############################################################################################"+bcolors.ENDC)
          print(UF.TimeStamp(),bcolors.BOLD+'Stage 1:'+bcolors.ENDC+' Sending hit cluster to the HTCondor, so tack segment combination pairs can be formed...')
          OptionHeader = [ " --MaxSegments ", " --ClassNames "," --ClassValues "]
          OptionLine = [MaxSegments,ClassNames,'"'+str(ClassValues)+'"']
          bad_pop=UF.CreateCondorJobs(AFS_DIR,EOS_DIR,
                                    '/ANNADEA/Data/TRAIN_SET/',
                                    'RawTrackSamples',
                                    'MCTr1a',
                                    '.pkl',
                                    TrainSampleID,
                                    JobSets,
                                    OptionHeader,
                                    OptionLine,
                                    'MCTr1a_GenerateRawTrackSamples_Sub.py',
                                    False)
          if len(bad_pop)==0:
              FreshStart=False
              print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 1 has successfully completed'+bcolors.ENDC)
              status=2
              continue

          if FreshStart:
              if (TotJobs)==len(bad_pop):
                  print(UF.TimeStamp(),bcolors.WARNING+'Warning, there are still', len(bad_pop), 'HTCondor jobs remaining'+bcolors.ENDC)
                  print(bcolors.BOLD+'If you would like to wait and exit please enter E'+bcolors.ENDC)
                  print(bcolors.BOLD+'If you would like to wait please enter enter the maximum wait time in minutes'+bcolors.ENDC)
                  print(bcolors.BOLD+'If you would like to resubmit please enter R'+bcolors.ENDC)
                  UserAnswer=input(bcolors.BOLD+"Please, enter your option\n"+bcolors.ENDC)
                  print(UF.TimeStamp(),'Submitting jobs to HTCondor... ',bcolors.ENDC)
                  if UserAnswer=='E':
                       print(UF.TimeStamp(),'OK, exiting now then')
                       exit()
                  if UserAnswer=='R':
                      bad_pop=UF.CreateCondorJobs(AFS_DIR,EOS_DIR,
                                    '/ANNADEA/Data/TRAIN_SET/',
                                    'RawTrackSamples',
                                    'MCTr1a',
                                    '.pkl',
                                    TrainSampleID,
                                    JobSets,
                                    OptionHeader,
                                    OptionLine,
                                    'MCTr1a_GenerateRawTrackSamples_Sub.py',
                                    True)
                      for bp in bad_pop:
                          UF.SubmitJobs2Condor(bp)
                  else:
                     if AutoPilot(600,10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RawTrackSamples','MCTr1a','.pkl',TrainSampleID,JobSets,OptionHeader,OptionLine,'MCTr1a_GenerateRawTrackSamples_Sub.py'):
                         FreshStart=False
                         print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 1 has successfully completed'+bcolors.ENDC)
                         status=2
                         continue
                     else:
                         print(UF.TimeStamp(),bcolors.FAIL+'Stage 1 is uncompleted...'+bcolors.ENDC)
                         status=6
                         break

              elif len(bad_pop)>0:
                   print(UF.TimeStamp(),bcolors.WARNING+'Warning, there are still', len(bad_pop), 'HTCondor jobs remaining'+bcolors.ENDC)
                   print(bcolors.BOLD+'If you would like to wait and exit please enter E'+bcolors.ENDC)
                   print(bcolors.BOLD+'If you would like to wait please enter enter the maximum wait time in minutes'+bcolors.ENDC)
                   print(bcolors.BOLD+'If you would like to resubmit please enter R'+bcolors.ENDC)
                   UserAnswer=input(bcolors.BOLD+"Please, enter your option\n"+bcolors.ENDC)
                   if UserAnswer=='E':
                       print(UF.TimeStamp(),'OK, exiting now then')
                       exit()
                   if UserAnswer=='R':
                      for bp in bad_pop:
                           UF.SubmitJobs2Condor(bp)
                      print(UF.TimeStamp(), bcolors.OKGREEN+"All jobs have been resubmitted"+bcolors.ENDC)
                      if AutoPilot(600,10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RawTrackSamples','MCTr1a','.pkl',TrainSampleID,JobSets,OptionHeader,OptionLine,'MCTr1a_GenerateRawTrackSamples_Sub.py'):
                          FreshStart=False
                          print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 1 has successfully completed'+bcolors.ENDC)
                          status=2
                          continue
                      else:
                          print(UF.TimeStamp(),bcolors.FAIL+'Stage 1 is uncompleted...'+bcolors.ENDC)
                          status=8
                          break
                   else:
                      if AutoPilot(int(UserAnswer),10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RawTrackSamples','MCTr1a','.pkl',TrainSampleID,JobSets,OptionHeader,OptionLine,'MCTr1a_GenerateRawTrackSamples_Sub.py'):
                          FreshStart=False
                          print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 1 has successfully completed'+bcolors.ENDC)
                          status=2
                          continue
                      else:
                          print(UF.TimeStamp(),bcolors.FAIL+'Stage 1 is uncompleted...'+bcolors.ENDC)
                          status=8
                          break
          else:
            if (TotJobs)==len(bad_pop):
                 bad_pop=UF.CreateCondorJobs(AFS_DIR,EOS_DIR,
                                    '/ANNADEA/Data/TRAIN_SET/',
                                    'RawTrackSamples',
                                    'MCTr1a',
                                    '.pkl',
                                    TrainSampleID,
                                    JobSets,
                                    OptionHeader,
                                    OptionLine,
                                    'MCTr1a_GenerateRawTrackSamples_Sub.py',
                                    True)
                 for bp in bad_pop:
                          UF.SubmitJobs2Condor(bp)


                 if AutoPilot(600,10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RawTrackSamples','MCTr1a','.pkl',TrainSampleID,JobSets,OptionHeader,OptionLine,'MCTr1a_GenerateRawTrackSamples_Sub.py'):
                        FreshStart=False
                        print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 1 has successfully completed'+bcolors.ENDC)
                        status=2
                        continue
                 else:
                     print(UF.TimeStamp(),bcolors.FAIL+'Stage 1 is uncompleted...'+bcolors.ENDC)
                     status=8
                     break

            elif len(bad_pop)>0:
                      for bp in bad_pop:
                           UF.SubmitJobs2Condor(bp)
                      if AutoPilot(600,10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RawTrackSamples','MCTr1a','.pkl',TrainSampleID,JobSets,OptionHeader,OptionLine,'MCTr1a_GenerateRawTrackSamples_Sub.py'):
                          FreshStart=False
                          print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 1 has successfully completed'+bcolors.ENDC)
                          status=2
                          continue
                      else:
                          print(UF.TimeStamp(),bcolors.FAIL+'Stage 1 is uncompleted...'+bcolors.ENDC)
                          status=8
                          break
      if status==2:
        print(bcolors.HEADER+"#############################################################################################"+bcolors.ENDC)
        print(UF.TimeStamp(),bcolors.BOLD+'Stage 2:'+bcolors.ENDC+' Collecting and de-duplicating the results from stage 1')
        for i in range(JobSets):
                req_file=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/'+'/'+'MCTr1a'+'_'+TrainSampleID+'_'+'RawTrackSamples'+'_'+str(i)+'.pkl'
                output_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/'+'/'+'MCTr1b'+'_'+TrainSampleID+'_'+'SelectedTrackSamples'+'_'+str(i)+'.pkl'
                base_data=UF.PickleOperations(req_file,'r', base_data)[1]
                print(len(ClassHeaders))
                exit()

                # Extracted0=[im for im in base_data if im.Label ==0]
                # Extracted1=[im for im in base_data if im.MC_truth_label ==1]
                # Extracted2=[im for im in base_data if im.MC_truth_label ==2]
                    #
                    # minLen = min(len(Extracted0), len(Extracted1), len(Extracted2))
                    # del base_data
                    # gc.collect()
                    #
                    # Extracted0=random.sample(Extracted0,minLen)
                    # Extracted1=random.sample(Extracted1,minLen)
                    #
                    # TotalData=[]
                    #
                    #
                    #
                    # TotalData=Extracted0+Extracted1+Extracted2
                    #
                    #
                    # write_data_file=open(req_file,'wb')
                    # pickle.dump(TotalData, write_data_file)
                    # write_data_file.close()
                    # del TotalData
                    # del Extracted0
                    # del Extracted1
                    # del Extracted2
                    # gc.collect()
                    # ProcessStatus=3



        print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 2 has successfully completed'+bcolors.ENDC)
        status=3
        continue

      # if status==3:
      #    print(bcolors.HEADER+"#############################################################################################"+bcolors.ENDC)
      #    print(UF.TimeStamp(),bcolors.BOLD+'Stage 3:'+bcolors.ENDC+' Taking the list of seeds previously generated by Stage 2, converting them into Emulsion Objects and doing more rigorous selection')
      #    JobSet=[]
      #    JobSets=Meta.JobSets
      #    for i in range(len(JobSets)):
      #        JobSet.append([])
      #        for j in range(len(JobSets[i][3])):
      #            JobSet[i].append(JobSets[i][3][j])
      #    TotJobs=0
      #    if type(JobSet) is int:
      #                   TotJobs=JobSet
      #    elif type(JobSet[0]) is int:
      #                   TotJobs=np.sum(JobSet)
      #    elif type(JobSet[0][0]) is int:
      #                   for lp in JobSet:
      #                       TotJobs+=np.sum(lp)
      #    OptionHeader = [" --MaxSTG ", " --MaxSLG ", " --MaxDOCA ", " --MaxAngle "," --ModelName "]
      #    OptionLine = [MaxSTG, MaxSLG, MaxDOCA, MaxAngle,'"'+str(ModelName)+'"']
      #    bad_pop=UF.CreateCondorJobs(AFS_DIR,EOS_DIR,
      #                               '/ANNADEA/Data/TRAIN_SET/',
      #                               'RefinedSeeds',
      #                               'MUTr1b',
      #                               '.pkl',
      #                               TrainSampleID,
      #                               JobSet,
      #                               OptionHeader,
      #                               OptionLine,
      #                               'MUTr1b_RefineSeeds_Sub.py',
      #                               False)
      #
      #    if FreshStart:
      #         if (TotJobs)==len(bad_pop):
      #            print(UF.TimeStamp(),bcolors.WARNING+'Warning, there are still', len(bad_pop), 'HTCondor jobs remaining'+bcolors.ENDC)
      #            print(bcolors.BOLD+'If you would like to wait and exit please enter E'+bcolors.ENDC)
      #            print(bcolors.BOLD+'If you would like to wait please enter enter the maximum wait time in minutes'+bcolors.ENDC)
      #            print(bcolors.BOLD+'If you would like to resubmit please enter R'+bcolors.ENDC)
      #            UserAnswer=input(bcolors.BOLD+"Please, enter your option\n"+bcolors.ENDC)
      #            print(UF.TimeStamp(),'Submitting jobs to HTCondor... ',bcolors.ENDC)
      #            if UserAnswer=='E':
      #                 print(UF.TimeStamp(),'OK, exiting now then')
      #                 exit()
      #            if UserAnswer=='R':
      #                bad_pop=UF.CreateCondorJobs(AFS_DIR,EOS_DIR,
      #                               '/ANNADEA/Data/TRAIN_SET/',
      #                               'RefinedSeeds',
      #                               'MUTr1b',
      #                               '.pkl',
      #                               TrainSampleID,
      #                               JobSet,
      #                               OptionHeader,
      #                               OptionLine,
      #                               'MUTr1b_RefineSeeds_Sub.py',
      #                               True)
      #                for bp in bad_pop:
      #                     UF.SubmitJobs2Condor(bp)
      #            else:
      #               if AutoPilot(600,10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RefinedSeeds','MUTr1b','.pkl',TrainSampleID,JobSet,OptionHeader,OptionLine,'MUTr1b_RefineSeeds_Sub.py',['',''],False,False):
      #                   FreshStart=False
      #                   print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 3 has successfully completed'+bcolors.ENDC)
      #                   status=4
      #                   continue
      #               else:
      #                   print(UF.TimeStamp(),bcolors.FAIL+'Stage 3 is uncompleted...'+bcolors.ENDC)
      #                   status=8
      #                   break
      #
      #         elif len(bad_pop)>0:
      #              print(UF.TimeStamp(),bcolors.WARNING+'Warning, there are still', len(bad_pop), 'HTCondor jobs remaining'+bcolors.ENDC)
      #              print(bcolors.BOLD+'If you would like to wait and exit please enter E'+bcolors.ENDC)
      #              print(bcolors.BOLD+'If you would like to wait please enter enter the maximum wait time in minutes'+bcolors.ENDC)
      #              print(bcolors.BOLD+'If you would like to resubmit please enter R'+bcolors.ENDC)
      #              UserAnswer=input(bcolors.BOLD+"Please, enter your option\n"+bcolors.ENDC)
      #              if UserAnswer=='E':
      #                  print(UF.TimeStamp(),'OK, exiting now then')
      #                  exit()
      #              if UserAnswer=='R':
      #                 for bp in bad_pop:
      #                      UF.SubmitJobs2Condor(bp)
      #                 print(UF.TimeStamp(), bcolors.OKGREEN+"All jobs have been resubmitted"+bcolors.ENDC)
      #                 if AutoPilot(600,10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RefinedSeeds','MUTr1b','.pkl',TrainSampleID,JobSet,OptionHeader,OptionLine,'MUTr1b_RefineSeeds_Sub.py',['',''],False,False):
      #                    FreshStart=False
      #                    print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 3 has successfully completed'+bcolors.ENDC)
      #                    status=4
      #                    continue
      #                 else:
      #                    print(UF.TimeStamp(),bcolors.FAIL+'Stage 3 is uncompleted...'+bcolors.ENDC)
      #                    status=8
      #                    break
      #              else:
      #
      #                 if AutoPilot(int(UserAnswer),10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RefinedSeeds','MUTr1b','.pkl',TrainSampleID,JobSet,OptionHeader,OptionLine,'MUTr1b_RefineSeeds_Sub.py',['',''],False,False):
      #                    FreshStart=False
      #                    print(UF.TimeStamp(),bcolors.OKGREEN+'Stage  has successfully completed'+bcolors.ENDC)
      #                    status=4
      #                    continue
      #                 else:
      #                    print(UF.TimeStamp(),bcolors.FAIL+'Stage 3 is uncompleted...'+bcolors.ENDC)
      #                    status=8
      #                    break
      #
      #         elif len(bad_pop)==0:
      #           FreshStart=False
      #           print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 3 has successfully completed'+bcolors.ENDC)
      #           status=4
      #           continue
      #    else:
      #       if (TotJobs)==len(bad_pop):
      #            bad_pop=UF.CreateCondorJobs(AFS_DIR,EOS_DIR,
      #                               '/ANNADEA/Data/TRAIN_SET/',
      #                               'RefinedSeeds',
      #                               'MUTr1b',
      #                               '.pkl',
      #                               TrainSampleID,
      #                               JobSet,
      #                               OptionHeader,
      #                               OptionLine,
      #                               'MUTr1b_RefineSeeds_Sub.py',
      #                               True)
      #            for bp in bad_pop:
      #                     UF.SubmitJobs2Condor(bp)
      #            if AutoPilot(600,10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RefinedSeeds','MUTr1b','.pkl',TrainSampleID,JobSet,OptionHeader,OptionLine,'MUTr1b_RefineSeeds_Sub.py',['',''],False,False):
      #                   FreshStart=False
      #                   print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 3 has successfully completed'+bcolors.ENDC)
      #                   status=4
      #                   continue
      #            else:
      #                print(UF.TimeStamp(),bcolors.FAIL+'Stage 3 is uncompleted...'+bcolors.ENDC)
      #                status=8
      #                break
      #
      #       elif len(bad_pop)>0:
      #                 for bp in bad_pop:
      #                      UF.SubmitJobs2Condor(bp)
      #                 print(UF.TimeStamp(), bcolors.OKGREEN+"All jobs have been resubmitted"+bcolors.ENDC)
      #                 if AutoPilot(600,10,Patience,AFS_DIR,EOS_DIR,'/ANNADEA/Data/TRAIN_SET/','RefinedSeeds','MUTr1b','.pkl',TrainSampleID,JobSet,OptionHeader,OptionLine,'MUTr1b_RefineSeeds_Sub.py',['',''],False,False):
      #                    FreshStart=False
      #                    print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 3 has successfully completed'+bcolors.ENDC)
      #                    status=4
      #                    continue
      #                 else:
      #                     print(UF.TimeStamp(),bcolors.FAIL+'Stage 3 is uncompleted...'+bcolors.ENDC)
      #                     status=8
      #                     break
      #       elif len(bad_pop)==0:
      #           FreshStart=False
      #           print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 3 has successfully completed'+bcolors.ENDC)
      #           status=4
      #           continue
      # if status==4:
      #   print(bcolors.HEADER+"#############################################################################################"+bcolors.ENDC)
      #   print(UF.TimeStamp(),bcolors.BOLD+'Stage 4:'+bcolors.ENDC+' Analysing the training samples')
      #   JobSet=[]
      #   for i in range(len(JobSets)):
      #        JobSet.append([])
      #        for j in range(len(JobSets[i][3])):
      #            JobSet[i].append(JobSets[i][3][j])
      #   for i in range(0,len(JobSet)):
      #        output_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1c_'+TrainSampleID+'_CompressedSeeds_'+str(i)+'.pkl'
      #        if os.path.isfile(output_file_location)==False:
      #           if os.path.isfile(EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1c_'+TrainSampleID+'_Temp_Stats.csv')==False:
      #              UF.LogOperations(EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1c_'+TrainSampleID+'_Temp_Stats.csv','w', [[0,0]])
      #           Temp_Stats=UF.LogOperations(EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1c_'+TrainSampleID+'_Temp_Stats.csv','r', '_')
      #
      #           TotalImages=int(Temp_Stats[0][0])
      #           TrueSeeds=int(Temp_Stats[0][1])
      #           base_data = None
      #           for j in range(len(JobSet[i])):
      #                    for k in range(JobSet[i][j]):
      #                         required_output_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1b_'+TrainSampleID+'_'+'RefinedSeeds'+'_'+str(i)+'_'+str(j) + '_' + str(k)+'.pkl'
      #                         new_data=UF.PickleOperations(required_output_file_location,'r','N/A')[0]
      #                         if base_data == None:
      #                               base_data = new_data
      #                         else:
      #                               base_data+=new_data
      #           try:
      #               Records=len(base_data)
      #               print(UF.TimeStamp(),'Set',str(i),'contains', Records, 'raw images',bcolors.ENDC)
      #
      #               base_data=list(set(base_data))
      #               Records_After_Compression=len(base_data)
      #               if Records>0:
      #                         Compression_Ratio=int((Records_After_Compression/Records)*100)
      #               else:
      #                         CompressionRatio=0
      #               TotalImages+=Records_After_Compression
      #               TrueSeeds+=sum(1 for im in base_data if im.Label == 1)
      #               print(UF.TimeStamp(),'Set',str(i),'compression ratio is ', Compression_Ratio, ' %',bcolors.ENDC)
      #               print(UF.PickleOperations(output_file_location,'w',base_data)[1])
      #           except:
      #               continue
      #           del new_data
      #           UF.LogOperations(EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1c_'+TrainSampleID+'_Temp_Stats.csv','w', [[TotalImages,TrueSeeds]])
      #   print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 4 has successfully completed'+bcolors.ENDC)
      #   status=5
      #   continue
      # if status==5:
      #      print(bcolors.HEADER+"#############################################################################################"+bcolors.ENDC)
      #      print(UF.TimeStamp(),bcolors.BOLD+'Stage 5:'+bcolors.ENDC+' Resampling the results from the previous stage')
      #      print(UF.TimeStamp(),'Sampling the required number of seeds',bcolors.ENDC)
      #      Temp_Stats=UF.LogOperations(EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1c_'+TrainSampleID+'_Temp_Stats.csv','r', '_')
      #      TotalImages=int(Temp_Stats[0][0])
      #      TrueSeeds=int(Temp_Stats[0][1])
      #      JobSet=[]
      #      for i in range(len(JobSets)):
      #        JobSet.append([])
      #        for j in range(len(JobSets[i][3])):
      #            JobSet[i].append(JobSets[i][3][j])
      #      if args.Samples=='ALL':
      #          if TrueSeeds<=(float(args.LabelRatio)*TotalImages):
      #              RequiredTrueSeeds=TrueSeeds
      #              RequiredFakeSeeds=int(round((RequiredTrueSeeds/float(args.LabelRatio))-RequiredTrueSeeds,0))
      #          else:
      #              RequiredFakeSeeds=TotalImages-TrueSeeds
      #              RequiredTrueSeeds=int(round((RequiredFakeSeeds/(1.0-float(args.LabelRatio)))-RequiredFakeSeeds,0))
      #
      #      else:
      #          NormalisedTotSamples=int(args.Samples)
      #          if TrueSeeds<=(float(args.LabelRatio)*NormalisedTotSamples):
      #              RequiredTrueSeeds=TrueSeeds
      #              RequiredFakeSeeds=int(round((RequiredTrueSeeds/float(args.LabelRatio))-RequiredTrueSeeds,0))
      #          else:
      #              RequiredFakeSeeds=NormalisedTotSamples*(1.0-float(args.LabelRatio))
      #              RequiredTrueSeeds=int(round((RequiredFakeSeeds/(1.0-float(args.LabelRatio)))-RequiredFakeSeeds,0))
      #      if TrueSeeds==0:
      #          TrueSeedCorrection=0
      #      else:
      #         TrueSeedCorrection=RequiredTrueSeeds/TrueSeeds
      #      if TotalImages-TrueSeeds>0:
      #       FakeSeedCorrection=RequiredFakeSeeds/(TotalImages-TrueSeeds)
      #      else:
      #        FakeSeedCorrection=0
      #      with alive_bar(len(JobSet),force_tty=True, title='Resampling the files...') as bar:
      #       for i in range(0,len(JobSet)):
      #         output_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1d_'+TrainSampleID+'_SampledCompressedSeeds_'+str(i)+'.pkl'
      #         input_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1c_'+TrainSampleID+'_CompressedSeeds_'+str(i)+'.pkl'
      #         bar.text = f'-> Resampling the file : {input_file_location}, exists...'
      #         bar()
      #         if os.path.isfile(output_file_location)==False and os.path.isfile(input_file_location):
      #             base_data=UF.PickleOperations(input_file_location,'r','N/A')[0]
      #             ExtractedTruth=[im for im in base_data if im.Label == 1]
      #             ExtractedFake=[im for im in base_data if im.Label == 0]
      #             del base_data
      #             gc.collect()
      #             ExtractedTruth=random.sample(ExtractedTruth,int(round(TrueSeedCorrection*len(ExtractedTruth),0)))
      #             ExtractedFake=random.sample(ExtractedFake,int(round(FakeSeedCorrection*len(ExtractedFake),0)))
      #             TotalData=[]
      #             TotalData=ExtractedTruth+ExtractedFake
      #             print(UF.PickleOperations(output_file_location,'w',TotalData)[1])
      #             del TotalData
      #             del ExtractedTruth
      #             del ExtractedFake
      #             gc.collect()
      #      print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 5 has successfully completed'+bcolors.ENDC)
      #      status=6
      #      continue
      # if status==6:
      #      print(bcolors.HEADER+"#############################################################################################"+bcolors.ENDC)
      #      print(UF.TimeStamp(),bcolors.BOLD+'Stage 6:'+bcolors.ENDC+' Preparing the final output')
      #      TotalData=[]
      #      JobSet=[]
      #      for i in range(len(JobSets)):
      #        JobSet.append([])
      #        for j in range(len(JobSets[i][3])):
      #            JobSet[i].append(JobSets[i][3][j])
      #
      #      for i in range(0,len(JobSet)):
      #          input_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/MUTr1d_'+TrainSampleID+'_SampledCompressedSeeds_'+str(i)+'.pkl'
      #          if os.path.isfile(input_file_location):
      #             base_data=UF.PickleOperations(input_file_location,'r','N/A')[0]
      #             TotalData+=base_data
      #      del base_data
      #      gc.collect()
      #      ValidationSampleSize=int(round(min((len(TotalData)*float(PM.valRatio)),PM.MaxValSampleSize),0))
      #      random.shuffle(TotalData)
      #      output_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/'+TrainSampleID+'_VAL_TRACK_SEEDS_OUTPUT.pkl'
      #      print(UF.PickleOperations(output_file_location,'w',TotalData[:ValidationSampleSize])[1])
      #      TotalData=TotalData[ValidationSampleSize:]
      #      print(UF.TimeStamp(), bcolors.OKGREEN+"Validation Set has been saved at ",bcolors.OKBLUE+output_file_location+bcolors.ENDC,bcolors.OKGREEN+'file...'+bcolors.ENDC)
      #      No_Train_Files=int(math.ceil(len(TotalData)/TrainSampleSize))
      #      with alive_bar(No_Train_Files,force_tty=True, title='Resampling the files...') as bar:
      #          for SC in range(0,No_Train_Files):
      #            output_file_location=EOS_DIR+'/ANNADEA/Data/TRAIN_SET/'+TrainSampleID+'_TRAIN_TRACK_SEEDS_OUTPUT_'+str(SC+1)+'.pkl'
      #            print(UF.PickleOperations(output_file_location,'w',TotalData[(SC*TrainSampleSize):min(len(TotalData),((SC+1)*TrainSampleSize))])[1])
      #            bar.text = f'-> Saving the file : {output_file_location}...'
      #            bar()
      #      print(UF.TimeStamp(),'Performing the cleanup... ',bcolors.ENDC)
      #      HTCondorTag="SoftUsed == \"ANNADEA-MUTr1a-"+TrainSampleID+"\""
      #      UF.TrainCleanUp(AFS_DIR, EOS_DIR, 'MUTr1a_'+TrainSampleID, ['MUTr1a'], HTCondorTag)
      #      HTCondorTag="SoftUsed == \"ANNADEA-MUTr1b-"+TrainSampleID+"\""
      #      UF.TrainCleanUp(AFS_DIR, EOS_DIR, 'MUTr1b_'+TrainSampleID, ['MUTr1b'], HTCondorTag)
      #      HTCondorTag="SoftUsed == \"ANNADEA-MUTr1c-"+TrainSampleID+"\""
      #      UF.TrainCleanUp(AFS_DIR, EOS_DIR, 'MUTr1c_'+TrainSampleID, ['MUTr1c'], HTCondorTag)
      #      HTCondorTag="SoftUsed == \"ANNADEA-MUTr1d-"+TrainSampleID+"\""
      #      UF.TrainCleanUp(AFS_DIR, EOS_DIR, 'MUTr1d_'+TrainSampleID, ['MUTr1d'], HTCondorTag)
      #      print(UF.TimeStamp(),bcolors.OKGREEN+'Stage 6 has successfully completed'+bcolors.ENDC)
      #      status=7
      #      continue
if status==7:
     print(UF.TimeStamp(), bcolors.OKGREEN+"Train sample generation has been completed"+bcolors.ENDC)
     exit()
else:
     print(UF.TimeStamp(), bcolors.FAIL+"Reconstruction has not been completed as one of the processes has timed out. Please run the script again (without Reset Mode)."+bcolors.ENDC)
     exit()



