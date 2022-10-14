# ANNADEA
Artificial Neural Network Driven Emulsion Analysis.
This README just serves as a very short user guide, the documentation will be written much later.

## 0. Hints and Tips
1) It is recommended to run those processes on lxplus in the tmux shell as some scripts can take up to several hours to execute.
2) The first letter of the script name prefixes indicate what kind of operations this script perform: R is for actual reconstruction routines, E for evaluation and M for model creation and training. I for Classification tasks.
3) The second letter of the script name prefixes indicates the subject of the reconstruction. H - hits, S - Track Segments, T- tracks, V - Vertices and E - events.
4) In general the numbers in prefixes reflect the order at which scripts have to be executed e.g: MH1, MH2,MH3. If there is no number then the script is independent or optional.
4) --help argument provides all the available run arguments of a script and its purpose.
5) The output of each script has the same prefix as the script that generates it. Sometimes if there are multiple sub scripts then the a,b,c letters are added to indicate the order of the execution. This is done for scripts with 'sub' suffix.
6) The files that are the final output will not have any suffixes.
   Those files are not deleted after execution. 
7) The screen output of the scripts is colour coded: 
   - White for routine operations
   - Blue for the file and folder locations
   - Green for successful operation completions
   - Yellow for warnings and non-critical errors.
   - Red for critical errors.
8) The white coloured text outputs with the prefix *UF* are the messages that are generated by imported functions in **UtilityFunction.py** file
9) Once the program successfully executes it will leave a following message before exiting: 
   "###### End of the program #####"

## 1. Tracking Module
The tracking module takes hits as an input and assigns the common ID - hence it clusters them into tracks.
All modules 
### Requirements

### 1.1 Installation steps
1) go to your home directory in afs where you would like to install the package
2) **git clone https://github.com/FilipsFedotovs/ANNADEA/**
3) **cd ANNADEA/**
4) **python setup.py**
5) The installation will require an EOS directory, please enter the location on EOS where you would like to keep data and the models. An example of the input is /eos/experiment/ship/user/username (but create the directory there first).
6) The installation will ask whether you want to copy default training and validation files (that were prepared earlier). Unless you have your own, please enter **Y**.     The installer will copy and analyse existing data, it might take 5-10 minutes
7) if the message *'ANNADEA setup is successfully completed'* is displayed, it means that the package is ready for work

### 1.2 Creating training files 
*This part is only needed if a new model is required*
1) Go to ANNADEA directory on AFS
2) **cd Code**
3) **tmux**
4) **kinit username@CERN.CH -l 24h00m**
5) Enter your lxplus password
6) **python3 MH1_GenerateTrainClusters.py --TrainSampleID Test_Sample --Xmin 50000 --Xmax 55000 --Ymin 50000 --Ymax 55000**
7) After few minutes the script will ask for the user option (Warning, there are still x HTCondor jobs remaining). Type **R** and press **Enter**. The script will submit the subscript jobs and go to the autopilot mode.
8) Exit tmux (by using **ctrl + b** and then typing  **d**). It can take up to few hours for HTCondor jobs to finish.
9) Enter the same tmux session after some period (after overnight job for example) by logging to the same lxplus machine and then typing  **tmux a -t 0**. The program should finish with the message *'Training samples are ready for the model creation/training'*

### 1.3 Reconstructing a hit data using the new model 
*This part is only needed if a new model is required*
1) Go to ANNADEA directory on AFS
2) **cd Code**
3) **tmux**
4) **kinit username@CERN.CH -l 24h00m**
5) Enter your lxplus password
6) **python3 MH2_TrainModel.py --TrainSampleID Test_Sample --ModelName Test_Model --ModelParams '[1,20,1,20]'**
7) The script will submit the subscript jobs and go to the autopilot mode.
8) Exit tmux (by using **ctrl + b** and then typing  **d**). Script will keep running in the autopilot mode until all the steps in the hit reconstruction process have been completed.
9) Enter the same tmux session (after overnight job for example) by logging to the same lxplus machine and then typing  **tmux a -t 0**. The program should finish with the message *'Training is finished then, thank you and goodbye'*

### 1.4 Reconstructing a hit data using the new model 
1) Go to ANNADEA directory on AFS
2) **cd Code**
3) **tmux**
4) **kinit username@CERN.CH -l 24h00m**
5) Enter your lxplus password
6) **python3 RH1_ReconstructHits.py --Log KALMAN --ModelName Test_Model --Xmin 50000 --Xmax 550000 --Ymin 50000 --Ymax 55000 --X_overlap 1 --Y_overlap 1 --Z_overlap 1 --RecBatchID Test_Batch**
7) The script will submit the subscript jobs and go to the autopilot mode.
8) Exit tmux (by using **ctrl + b** and then typing  **d**). Script will keep running in the autopilot mode until all the steps in the hit reconstruction process have been completed.
9) Enter the same tmux session (after overnight job for example) by logging to the same lxplus machine and then typing  **tmux a -t 0**. The program should finish with the message *'Reconstruction has been completed'*


