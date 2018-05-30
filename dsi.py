#!/usr/bin/env python3
""" 'dsi.py': DataSetInfo for LAT.
    C. Wiseman, 18 March 2018
"""
import os, json, glob, re
import numpy as np
import tinydb as db

latSWDir    = os.environ['LATDIR']
dataDir     = os.environ['LATDATADIR']
bkgDir      = dataDir+"/bkg"     # subfolders: skim waves split lat thresh cut
calDir      = dataDir+"/cal"     # subfolders: skim waves split lat eff
specialDir  = dataDir+"/special" # subfolders: skim waves split lat
skimDir     = bkgDir+"/skim"
waveDir     = bkgDir+"/waves"
splitDir    = bkgDir+"/split"
latDir      = bkgDir+"/lat"
cutDir      = bkgDir+"/cut"
calSkimDir  = calDir+"/skim"
calWaveDir  = calDir+"/waves"
calSplitDir = calDir+"/split"
calLatDir   = calDir+"/lat"
effDir      = calDir+"/eff"
pandaDir    = dataDir+"/pandas"
threshDir   = bkgDir+"/thresh"

class BkgInfo:
    def __init__(self):
        with open("%s/data/runsBkg.json" % latSWDir) as f:
            self.master = scrubDict(json.load(f))

    def dsMap(self):
        """returns {ds:numSubDS}"""
        numSubDS = {}
        for key in sorted(list(self.master)):
            last = int(list(self.master[key].keys())[-1])
            numSubDS[int(key)] = last
        return numSubDS

    def dsRanges(self):
        """ Manual edit.  Cover all runs in BG list and also cal runs.
        Verified, 12 Apr 2018 CGW. (DS6 is incomplete)
        """
        return {
            0:[2571,7614],
            1:[9407,14502],
            2:[14699,15892],
            3:[16797,18589],
            4:[60000791,60002394],
            5:[18623,25508],
            6:[25672,100000]
        }

    def getRanges(self, ds):
        """ {sub:[runLo1,runHi1, runLo2,runHi2 ...]}"""
        if ds=="5A":
            return {i:self.master[5][i] for i in range(0,79+1)}
        elif ds=="5B":
            return {i:self.master[5][i] for i in range(80,112+1)}
        elif ds=="5C":
            return {i:self.master[5][i] for i in range(113,121+1)}
        else:
            return self.master[int(ds)]

    def getRunList(self, ds, sub=None):
        bkgRanges = self.getRanges(ds)
        runList = []
        if sub is None:
            for ds in sorted(bkgRanges.keys()):
                subRange = bkgRanges[ds]
                for i in range(0,len(subRange),2):
                    runLo, runHi = subRange[i], subRange[i+1]
                    for r in range(runLo, runHi+1):
                        runList.append(r)
        else:
            subRange = bkgRanges[sub]
            for i in range(0,len(subRange),2):
                runLo, runHi = subRange[i], subRange[i+1]
                for r in range(runLo, runHi+1):
                    runList.append(r)
        return runList

    def GetDSNum(self,run):
        ranges = self.dsRanges()
        for ids in range(len(ranges)):
            if ranges[ids][0] <= run <= ranges[ids][1]:
                dsNum = ids
        return dsNum

    def GetBkgIdx(self, dsNum, runNum):
        """ Finds the bkgIdx of a given run.  Must be IN the dataset! """
        bkgRuns = self.master[dsNum]

        for bkgIdx in bkgRuns:
            runCov = bkgRuns[bkgIdx]
            runList = []
            for idx in range(0,len(runCov),2):
                runList.extend(list(range(runCov[idx],runCov[idx+1]+1)))
            if runNum in runList:
                return bkgIdx
        return -1

    def GetSubRanges(self, ds=None, sub=None, opt="thr"):
        """ Return the sub-sub ranges defined by running the threshold finder,
        or changing detector HV. Generated by LAT/chan-sel.py::getSubRanges.
        """
        f = np.load("%s/data/thrHV_subRanges.npz" % os.environ['LATDIR'])
        thRanges = f['arr_0']
        hvRanges = f['arr_1']
        tmpRanges = []
        if opt == "thr": tmpRanges = thRanges
        elif opt == "hv":  tmpRanges = hvRanges
        else:
            print("IDK what this option is.")
            return None
        if ds is None: return tmpRanges

        subRanges = []
        for val in tmpRanges:  # val:(ds, sub, runLo, runHi, nRuns)

            if sub is None and ds==val[0]:
                subRanges.append(val)

            # specific lookup
            if sub is not None and ds is not None:
                if ds==val[0] and sub==val[1]:
                    subRanges.append((val[2], val[3]))

        return subRanges


class CalInfo:
    def __init__(self):
        with open("%s/data/runsCal.json" % latSWDir) as f:
            self.master = scrubDict(json.load(f),'cal')
        with open("%s/data/runsSpecial.json" % latSWDir) as f:
            self.special = scrubDict(json.load(f),'cal')

        # Track all the 'hi' run coverage numbers for fast run range lookups
        self.covIdx = {}
        for key in self.master:
            tmp = []
            for idx in self.master[key]:
                tmp.append(self.master[key][idx][2])
            self.covIdx[key] = np.asarray(tmp)

    def GetMasterList(self):
        return self.master

    def GetCovArr(self,key):
        return self.covIdx[key]

    def GetIdxs(self,key):
        return len(self.covIdx[key])

    def GetKeys(self,dsNum=None):
        keyList = sorted(self.master.keys())
        if dsNum==None:
            return keyList
        else:
            thisDSList = []
            for key in keyList:
                if "ds%d" % dsNum in key: thisDSList.append(key)
            return thisDSList

    def GetCalIdx(self,key,run):
        """ Look up the calibration index corresponding to a particular run. """
        if key not in self.covIdx:
            print("Key %s not found in master list!" % key)
            return None

        idx = np.searchsorted(self.covIdx[key], run)
        if idx not in self.master[key]:
            print("Run %d out of range of key %s.  calIdx was %d" % (run, key, idx))
            return None
        lst = self.master[key][idx]
        lo, hi = lst[1], lst[2]
        if lo <= run <= hi:
            return idx
        else:
            print("Run %d not found with key %s, lo=%d hi=%d" % (run,key,lo,hi))
            return None

    def GetNCalIdxs(self,dsNum,module):
        """ Get the number of calIdx's in a given dataset. """
        calKeys = self.GetKeys(dsNum)
        for key in calKeys:
            if "m%d" % module in key:
                return self.GetIdxs(key)
        if module==-1:
            return self.GetIdxs(key)
        return 0

    def GetCalList(self,key,idx,runLimit=None):
        """ Generate a list of runs for a given calibration index. """
        if key not in self.master:
            print("Key %s not found in master list!" % key)
            return None

        runList = []
        if idx not in self.master[key].keys():
            return None
        lst = self.master[key][idx][0]
        for i in range(0,len(lst),2):
            lo, hi = lst[i], lst[i+1]
            runList += range(lo, hi+1)
        if runLimit is not None:
            del runList[runLimit:]
        return runList

    def GetCalRunCoverage(self,key,idx):
        """ Return the (runLo, runHi) coverage of a particular calIdx"""
        if key not in self.master:
            print("Key %s not found in master list!" % key)
            return None
        return self.master[key][idx][1], self.master[key][idx][2]

    def GetCalFiles(self, dsNum, calIdx=None, modNum=None, verbose=False, cDir=calDir):
        """ Get a list of all files for a particular dsNum+calIdx.
            This will match the cut record entries in the DB.
        """
        calKeys = self.GetKeys(dsNum)

        fList = []
        for key in calKeys:
            if modNum is not None and str(modNum) not in key:
                continue
            if verbose: print(key)
            nIdx = self.GetIdxs(key)  # number of cal subsets

            # get the runs in each calIdx
            runList = []
            if calIdx!=None:
                runList = self.GetCalList(key, calIdx, 10)
                if verbose: print(runList)
            else:
                for idx in range(nIdx):
                    tmp = self.GetCalList(key, idx, 10)
                    if verbose: print(tmp)
                    runList += tmp

            # make a list of the actual file paths
            for run in runList:
                fPath = "%s/latSkimDS%d_run%d*.root" % (calDir, dsNum, run)
                fList += glob.glob(fPath)

        # for f in fList: print(f)
        return fList

    def GetSpecialKeys(self):
        return self.special.keys()

    def GetSpecialNIdxs(self,key):
        return len(self.special[key])

    def GetSpecialRuns(self,key,idx=None):

        noFiles = [6936,6937,6940,6942,6944,6965,6968,6969,6974,6977,7224,7267,7268,7269,7270,7271,7272,13168]

        if idx is not None:
            runLo, runHi = self.special[key][idx][0], self.special[key][idx][1]
            runList = [run for run in range(runLo, runHi+1) if run not in noFiles]
            return runList

        runList = []
        for idx in self.special[key].keys():
            runLo, runHi = self.special[key][idx][0], self.special[key][idx][1]
            runList.extend([run for run in range(runLo, runHi+1) if run not in noFiles])
        return runList

    def GetSpecialList(self):
        return self.special


class DetInfo:
    def __init__(self):
        self.dets = {}
        self.dets["M1"] = [
            '111', '112', '113', '114',
            '121', '122', '123', '124',
            '131', '132', '133', '134',
            '141', '142', '143', '144', '145',
            '151', '152', '153', '154',
            '161', '162', '163', '164',
            '171', '172', '173', '174'
            ]
        self.dets["M2"] = [
            '211', '212', '213', '214',
            '221', '222', '223', '224', '225',
            '231', '232', '233',
            '241', '242', '243', '244', '245',
            '251', '252', '253', '254',
            '261', '262', '263', '264',
            '271', '272', '273', '274'
            ]
        self.allDets = self.dets["M1"] + self.dets["M2"]

        self.detIDs = {}
        self.detIDs["M1"] = {
            '111':1426981, '112':1425750, '113':1426612, '114':1425380,
            '121':28474, '122':1426640, '123':1426650, '124':1426622,
            '131':28480, '132':1426980, '133':1425381, '134':1425730,
            '141':28455, '142':28470, '143':28463, '144':28465, '145':28469,
            '151':28477, '152':1425751, '153':1426610, '154':1425731,
            '161':1425742, '162':1426611, '163':1425740, '164':1426620,
            '171':28482, '172':1425741, '173':1426621, '174':1425370
        }
        self.detIDs["M2"] = {
            '211':28459, '212':1426641, '213':1427481, '214':1427480,
            '221':28481, '222':28576, '223':28594, '224':28595, '225':28461,
            '231':1427490, '232':1427491, '233':1428530,
            '241':28607, '242':28456, '243':28621, '244':28466, '245':28473,
            '251':28487, '252':1426651, '253':1428531, '254':1427120,
            '261':1235170, '262':1429091, '263':1429092, '264':1426652,
            '271':28619, '272':1427121, '273':1429090, '274':28717
        }
        self.allDetIDs = {}
        self.allDetIDs.update(self.detIDs["M1"])
        self.allDetIDs.update(self.detIDs["M2"])

        self.detActiveMass = {}
        # if this is really annoying to have it by detector ID, come back and change it to CPD
        # note: DataSetInfo.hh also has the active mass uncertainties if we need those too.
        self.detActiveMass["M1"] = {
            1426981: 510, 1425750: 979, 1426612: 811, 1425380: 968,
            28474: 560, 1426640: 723, 1426650: 659, 1426622: 689,
            28480: 551, 1426980: 886, 1425381: 949, 1425730: 1024,
            28455: 558, 28470: 564, 28463: 567, 28465: 545, 28469: 557,
            28477: 553, 1425751: 730, 1426610: 632, 1425731: 982,
            1425742: 732, 1426611: 675, 1425740: 701, 1426620: 572.2,
            28482: 561, 1425741: 710, 1426621: 590.8, 1425370: 964
        }
        self.detActiveMass["M2"] = {
            28459: 556, 1426641: 576, 1427481: 903, 1427480: 917,
            28481: 581, 28576: 562, 28594: 559, 28595: 558, 28461: 577,
            1427490: 872, 1427491: 852, 1428530: 996, 28607: 558,
            28456: 579, 28621: 565, 28466: 566, 28473: 562, 28487: 557,
            1426651: 591, 1428531: 1031, 1427120: 802, 1235170: 462.2,
            1429091: 775, 1429092: 821, 1426652: 778,
            28619: 566, 1427121: 968, 1429090: 562, 28717: 567
        }
        self.allActiveMasses = {}
        self.allActiveMasses.update(self.detActiveMass["M1"])
        self.allActiveMasses.update(self.detActiveMass["M2"])

        # -- Load outputs from LAT/chan-sel.py --
        # Generated with LAT/chan-sel.py::fillDetInfo
        # Used BKG ranges, DS0-6 in LAT/data/runsBkg.json
        # (verified to 100% match DataSetInfo.cc, (14 Apr 2018 CGW))
        f = np.load("%s/data/runSettings-v2.npz" % os.environ['LATDIR'])
        self.detHV = f['arr_0'].item()
        self.detTH = f['arr_1'].item()
        self.detCH = f['arr_2'].item()
        self.pMons = f['arr_3'].item()

    def getPMon(self,ds=None):
        """ {ds : [chan1, chan2 ...] }
        Analysis channel numbers of 'special' channels.
        """
        if ds is None: return self.pMons
        else: return self.pMons[ds]

    def getHV(self,ds=None,cpd=None):
        """ {ds : {'det' : [(run1,val1),(run2,val2)...]} }
        HV settings for the first run they apply to.
        If there are multiple entries in the list, HV was changed
        at run number 'run2' to 'val2', and so on.
        (Caveat: actual run that HV changed may be BETWEEN bkg run indexes.)
        """
        if ds is None and cpd is None:
            return self.detHV
        elif cpd is None:
            return self.detHV[ds]
        else:
            return self.detHV[ds][cpd]

    def getHVAtRun(self,ds,run,opt="cpd"):
        """ {cpd : HV} or {chan : HV} depending on option.
        Sets detectors w/ no entry to 0V (which is true).

        TODO: this needs to use the result from chan-sel::checkAllRunsHV

        """
        hv = self.detHV[ds] # {cpd : [(run1,hv1),(run2,hv2),...] }
        # for h in sorted(hv): print(h, hv[h])
        # return

        out = {}
        for cpd in sorted(hv):

            if len(hv[cpd]) == 0:
                chanHV = 0
            else:
                hvInit = hv[cpd][0][1]
                runInit = hv[cpd][0][0]
                if run < runInit:
                    # print("Run not covered in this DS! run:%d, runInit %d" % (run, runInit))
                    chanHV = 0

                # find the HV setting for this run
                for r,h in hv[cpd]:
                    if run < r: continue
                    if run >= r: chanHV = h
                    if r > run: break
                # print("run:",run,"cpd:",cpd,"chanHV:",chanHV)

                if opt == "cpd":
                    out[str(cpd)] = chanHV
                if opt == "chan":
                    out[self.getCPDChan(ds,str(cpd))] = chanHV
        return out

    def getTH(self,ds=None,cpd=None):
        """ {ds : {'det' : [(run1,val1),(run2,val2)...]} }
        TRAP threshold settings for the first run they apply to. Same caveat as 'getHV' above.
        """
        if ds is None and cpd is None:
            return self.detTH
        elif cpd is None:
            return self.detTH[ds]
        else:
            return self.detTH[ds][cpd]

    def getTrapThreshAtRun(self,ds,run,opt="cpd"):
        """ {cpd : trap thresh} or {chan : trap thresh} depending on option.
        Sets detectors w/ no thresh value (not active in this DS) to -1.
        """
        th = self.detTH[ds] # {cpd : [(run1,trap1),(run2,trap2),...]}
        # for t in sorted(th): print(t, th[t])
        # return

        out = {}
        for cpd in sorted(th):

            if len(th[cpd]) == 0:
                chanTH = -1
            else:
                thInit = th[cpd][0][1]
                runInit = th[cpd][0][0]
                if run < runInit:
                    # print("Run not covered in this DS! run:%d, runInit %d" % (run, runInit))
                    chanTH = -1

                # find the trap threshold setting for this run
                for r,t in th[cpd]:
                    if run < r: continue
                    if run >= r: chanTH = t
                    if r > run: break
                # print("run:",run,"cpd:",cpd,"chanTH:",chanTH)

                if opt == "cpd":
                    out[str(cpd)] = chanTH
                if opt == "chan":
                    out[self.getCPDChan(ds,str(cpd))] = chanTH
        return out

    def getCH(self,ds=None,cpd=None):
        """ {ds : {'det' : [(run1,val1),(run2,val2)...]} }
        Value of the HG analysis channel for a particular detector.
        Uses results from LAT/chan-sel.py::getSettings.
        """
        if ds is None and cpd is None:
            return self.detCH
        elif cpd is None:
            return self.detCH[ds]
        else:
            return self.detCH[ds][cpd]

    def getChanList(self,ds):
        """In DS0-6, the channel number does NOT change in the DS."""
        return sorted([ch[0][1] for ch in self.detCH[ds].values() if len(ch)>0])

    def getChanCPD(self,ds,chan):
        """ Get the CPD of a channel """
        cpd = {val[0][1]:cpd for cpd, val in self.detCH[ds].items() if len(val)>0}
        if chan in cpd.keys():
            return cpd[chan]
        else:
            return None

    def getCPDChan(self,ds,cpd):
        """ Get the channel of a cpd """
        chan = {cpd:val[0][1] for cpd, val in self.detCH[ds].items() if len(val)>0}
        if cpd in chan.keys():
            return chan[cpd]
        else:
            return None

    def getChanDetID(self,ds,detID):
        """ Given a detID (ex. 1426641), get its channel.
        Returns nothing if the detector isn't enabled in this DS.
        """
        cpdToChan = {cpd:chan[0][1] for cpd, chan in self.detCH[ds].items() if len(chan)>0}
        detIDtoCPD = {id:cpd for cpd, id in self.allDetIDs.items()}

        if detIDtoCPD[detID] in cpdToChan.keys(): # i.e. it's active at some point in the DS
            return cpdToChan[detIDtoCPD[detID]]
        else:
            return None

    def getDetIDChan(self,ds,chan):
        """ Given a channel, return a detID. """
        return self.allDetIDs[self.getChanCPD(ds,chan)]

    def getBadDetIDList(self, ds):
        """ Matches DataSetInfo.cc::LoadBadDetectorMap, 4 Apr 2018, CGW """
        if ds==0: return [28474, 1426622, 28480, 1426980, 1426620, 1425370]
        if ds==1: return [1426981, 1426622, 28455, 28470, 28463, 28465, 28469, 28477, 1425751, 1425731, 1426611]
        if ds==2: return [1426981, 1426622, 28455, 28470, 28463, 28465, 28469, 28477, 1425731, 1426611]
        if ds==3: return [1426981, 1426622, 28477, 1425731, 1426611]
        if ds==4: return [28595, 28461, 1428530, 28621, 28473, 1426651, 1429092, 1426652, 28619]
        if ds==5: return [1426981, 1426622, 28477, 1425731, 1426611, 28595, 28461,
            1428530, 28621, 28473, 1426651, 1429092, 1426652, 28619, 1427121]
        if ds==6: return [1426981, 28474, 1426622, 28477, 1425731, 1426611, 28595,
            28461, 1428530, 28621, 28473, 1426651, 1429092, 1426652, 28619, 1427121]

    def getVetoDetIDList(self, ds):
        """ Matches DataSetInfo.cc::LoadVetoDetectorMap, 4 Apr 2018, CGW """
        if ds==0: return [1425381, 1425742]
        if ds==1: return [28480]
        if ds==2: return [28480, 1425751, 1426621]
        if ds==3: return [28480, 28470, 28463]
        if ds==4: return [28459, 1426641, 1427481, 28456, 1427120, 1427121]
        if ds==5: return [28480, 1426641, 1427481, 1235170]
        if ds==6: return [28480, 1426641, 1427481, 1235170]

    def getBadChanList(self, ds):
        """ Return a list of bad and veto-only HG channels for a DS """
        badIDs = self.getBadDetIDList(ds) + self.getVetoDetIDList(ds)
        badChans = [self.getChanDetID(ds, id) for id in badIDs if self.getChanDetID(ds,id) is not None]
        return badChans

    def getGoodChanList(self, ds, mod=None, detType=None):
        """ Return a list of good HG channels for a DS.  No bad, no veto-only, no pulser monitors. """
        chList = self.getChanList(ds)
        badList = self.getBadChanList(ds)
        goodList = [ch for ch in chList if ch not in badList and ch not in self.pMons[ds]]

        if mod==1:
            goodList = [ch for ch in goodList if ch < 1000]
        elif mod==2:
            goodList = [ch for ch in goodList if ch > 1000]

        if detType is None:
            return goodList
        elif detType == "Enr":
            return [ch for ch in goodList if self.getDetIDChan(ds,ch) > 1000000]
        elif detType == "Nat":
            return [ch for ch in goodList if self.getDetIDChan(ds,ch) < 1000000]
        else:
            print("IDK what that detType is.")
            return None

    def getDetectorList(self, ds, chanList):
        """ Convert a list of channels into a list of detector CPDs. """
        return[self.getChanCPD(ds,ch) for ch in chanList]


class SimInfo:
    """ Adapted from ~mjdsim/analysisScriptsV2/analysisUtilities.py """
    dets = {}
    dets["M1"] = ['1010101', '1010102', '1010103', '1010104',
        '1010201', '1010202', '1010203', '1010204',
        '1010301', '1010302', '1010303', '1010304',
        '1010401', '1010402', '1010403', '1010404', '1010405',
        '1010501', '1010502', '1010503', '1010504',
        '1010601', '1010602', '1010603', '1010604',
        '1010701', '1010702', '1010703', '1010704']
    dets["M2"] = ['1020101', '1020102', '1020103', '1020104',
        '1020201', '1020202', '1020203', '1020204', '1020205',
        '1020301', '1020302', '1020303',
        '1020401', '1020402', '1020403', '1020404', '1020405',
        '1020501', '1020502', '1020503', '1020504',
        '1020601', '1020602', '1020603', '1020604',
        '1020701', '1020702', '1020703', '1020704']
    detectors = dets["M1"] + dets["M2"]

    activeDets = {}
    activeDets["M1"] = {
              # C1P1         C1P2         C1P3         C1P4            C1P5         C1P6         C1P7
        'All':[	1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1],
        'DS0':[	1, 1, 1, 1,  0, 1, 1, 0,  0, 0, 0, 1,  1, 1, 1, 1, 1,  1, 1, 1, 1,  0, 1, 1, 0,  1, 1, 1, 0],
        'DS1':[	0, 1, 1, 1,  1, 1, 1, 0,  0, 1, 1, 1,  0, 0, 0, 0, 0,  0, 0, 1, 0,  1, 0, 1, 1,  1, 1, 1, 1],
        'DS2':[	0, 1, 1, 1,  1, 1, 1, 0,  0, 1, 1, 1,  0, 0, 0, 0, 0,  0, 0, 1, 0,  1, 0, 1, 1,  1, 1, 0, 1],
        'DS3':[	0, 1, 1, 1,  1, 1, 1, 0,  0, 1, 1, 1,  1, 0, 0, 1, 1,  0, 1, 1, 0,  1, 0, 1, 1,  1, 1, 1, 1],
        'DS4':[	0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0],
        'DS5':[	0, 1, 1, 1,  1, 1, 1, 0,  0, 1, 1, 1,  1, 1, 1, 1, 1,  0, 1, 1, 0,  1, 0, 1, 1,  1, 1, 1, 1]
        }
    activeDets["M2"] = {
        'All':[	1, 1, 1, 1,  1, 1, 1, 1, 1,  1, 1, 1,  1, 1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1],
        'DS0':[	0, 0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0],
        'DS1':[	0, 0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0],
        'DS2':[	0, 0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0],
        'DS3':[	0, 0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0,  0, 0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0],
        'DS4':[	0, 0, 0, 1,  1, 1, 1, 0, 0,  1, 1, 0,  1, 0, 0, 1, 0,  1, 0, 1, 0,  1, 1, 0, 0,  0, 0, 1, 1],
        'DS5':[	1, 0, 0, 1,  1, 1, 1, 0, 0,  1, 1, 0,  1, 1, 0, 1, 0,  1, 0, 1, 1,  0, 1, 0, 0,  0, 0, 1, 1]
        }

    dtCutoffs = {}  #  P1           P2            P3            P4              P5           P6           P7
    dtCutoffs["M1"] = [7, 7, 6, 6,  8, 8, 7, 6,   6, 6, 8, 8,   6, 6, 6, 6, 7,  6, 8, 7, 8,  6, 6, 6, 6,  7, 7, 6, 9]
    dtCutoffs["M2"] = [6, 7, 5, 6,  6, 6, 6, 6, 6,   7, 8, 8,   6, 6, 6, 5, 6,  6, 7, 6, 6,  7, 9, 6, 6,  6, 7, 7, 5]

    def __init__(self, config):
        self.config = config

    def GetDetectorList(self, module=None):
        return (self.detectors if module is None else self.dets[module])

    def GetActiveDets(self, config, module):
        detList = []
        for iD, det in enumerate(self.GetDetectorList(module)):
            if self.activeDets[module][config][iD] == 1:
                detList.append(det)
        return detList

    def GetDTCutoff(self, module, detector):
        iD = self.dets[module].index(detector)
        return self.dtCutoffs[module][iD]


def scrubDict(myDict,opt=''):
    """ Create appropriate python dicts from our run list json files. """
    for key in list(myDict):
        if "note" in key:
            del myDict[key]
            continue
        for key2 in list(myDict[key]):
            if "note" in key2:
                del myDict[key][key2]

    if opt=='cal':
        makeIntKeys = {key:{int(key2):myDict[key][key2] for key2 in myDict[key]} for key in myDict}
        return makeIntKeys
    else:
        makeIntKeys = {int(key):{int(key2):myDict[key][key2] for key2 in myDict[key]} for key in myDict}
        return makeIntKeys


def getSplitList(filePathRegexString, subNum, uniqueKey=False, dsNum=None):
    """ Creates a dict of files w/ the format {'DSX_X_X':filePath.}
        Used to combine and split apart files during the LAT processing.
        Used in place of sorted(glob.glob(myPath)).
    """
    files = {}
    for fl in glob.glob(filePathRegexString):
        int(re.search(r'\d+',fl).group())
        pathList = os.path.split(fl)
        for path in pathList:
            if '.root' in path:
                ints = list(map(int, re.findall(r'\d+', path)))
        if (ints[1]==subNum):
            if (len(ints)==2):
                ints.append(0)
            if not uniqueKey:
                files[ints[2]] = fl # zero index
            else:
                files["DS%d_%d_%d" % (dsNum,subNum,ints[2])] = fl
    return files


def GetExposureDict(dsNum, modNum, dPath="%s/data" % latSWDir, verbose=False):
    """ Parse granular exposure output from ds_livetime.cc """

    chList = GetGoodChanList(dsNum)
    if dsNum==5 and modNum==1: chList = [ch for ch in chList if ch < 1000 and ch!=692]
    if dsNum==5 and modNum==2: chList = [ch for ch in chList if ch > 1000 and ch!=1232]

    expDict = {ch:[] for ch in chList}
    tmpDict, bkgIdx, prevBkgIdx = {}, -1, -1

    with open("%s/expos_ds%d.txt" % (dPath, dsNum), "r") as f:
        table = f.readlines()

    for idx, line in enumerate(table):
        tmp = (line.rstrip()).split(" ")
        if len(tmp)==0: continue

        if bkgIdx != prevBkgIdx:
            for ch in chList:
                if ch in tmpDict.keys():
                    expDict[ch].append(tmpDict[ch])
                else:
                    expDict[ch].append(0.)
            tmpDict = {}
            prevBkgIdx = bkgIdx

        if tmp[0] == "bkgIdx":
            bkgIdx = tmp[1]

        if len(tmp) > 1 and tmp[1] == ":" and tmp[0].isdigit() and int(tmp[0]) in chList:
            ch, exp = int(tmp[0]), float(tmp[2])
            tmpDict[ch] = exp

        if line == "All-channel summary: \n":
            summaryIdx = idx

    # get last bkgIdx
    for ch in chList:
        if ch in tmpDict.keys():
            expDict[ch].append(tmpDict[ch])
        else:
            expDict[ch].append(0.)

    # knock off the first element (it's 0).  Now expDict is done
    for ch in expDict:
        if expDict[ch][0] > 0:
            print("ERROR, WTF")
            exit(1)
        expDict[ch].pop(0)

    # now get the all-channel summary for HG channels
    summaryDict = {ch:[] for ch in chList}
    for line in table[summaryIdx+2:]:
        tmp = (line.rstrip()).split()
        ch, detID, aMass, runTime, expo = int(tmp[0]), int(tmp[1]), float(tmp[2]), float(tmp[3]), float(tmp[4])
        summaryDict[ch] = [expo, aMass]

    # now a final cross check
    if verbose:
        print("DS%d, M%d" % (dsNum, modNum))
    for ch in chList:

        if sum(expDict[ch]) > 0 and len(summaryDict[ch]) == 0:
            print("That ain't shoulda happened")
            exit(1)
        elif len(summaryDict[ch]) == 0:
            continue;

        mySum, ltResult, aMass = sum(expDict[ch]), summaryDict[ch][0], summaryDict[ch][1]
        diff = ((ltResult-mySum)/aMass) * 86400

        if verbose:
            print("%d   %.4f   %-8.4f    %-8.4f    %-8.4f" % (ch, aMass, mySum, ltResult, diff))

    return expDict


def getDBRecord(key, verbose=False, calDB=None, pars=None):
    """ View a particular database record. """
    import tinydb as db

    if calDB is None: calDB = db.TinyDB('calDB.json')
    if pars is None: pars = db.Query()

    recList = calDB.search(pars.key == key)
    nRec = len(recList)
    if nRec == 0:
        if verbose: print("Record %s doesn't exist" % key)
        return 0
    elif nRec == 1:
        if verbose: print("Found record:\n%s" % key)
        rec = recList[0]['vals']  # whole record

        # sort the TinyDB string keys numerically (obvs only works for integer keys)
        result = {}
        for key in sorted([int(k) for k in rec]):
            if verbose: print(key, rec[u'%d' % key])
            result[key] = rec[u'%d' % key]
        return result
    else:
        print("WARNING: Found multiple records for key: %s.  Need to do some cleanup!" % key)
        for rec in recList:
            for key in sorted([int(k) for k in rec]):
                print(key, rec[u'%d' % key])
            print(" ")


def setDBRecord(entry, forceUpdate=False, dbFile="calDB.json", calDB=None, pars=None, verbose=False):
    """ Adds entries to the DB. Checks for duplicate records.
    The format of 'entry' should be a nested dict:
    myEntry = {"key":key, "vals":vals}
    """
    import tinydb as db
    if calDB is None:
        calDB = db.TinyDB(dbFile)
        pars = db.Query()

    key, vals = entry["key"], entry["vals"]
    recList = calDB.search(pars.key==key)
    nRec = len(recList)
    if nRec == 0:
        if verbose: print("Record '%s' doesn't exist in the DB  Adding it ..." % key)
        calDB.insert(entry)
    elif nRec == 1:
        prevRec = recList[0]['vals']
        if prevRec!=vals:
            if verbose:
                print("An old version of record '%s' exists.  It DOES NOT match the new version.  forceUpdate? %r" % (key, forceUpdate))
            if forceUpdate:
                if verbose:
                    print("Updating record: ",key)
                calDB.update(entry, pars.key==key)
    else:
        print("WARNING: Multiple records found for key '%s'.  Need to do some cleanup!!")


def GetDBCuts(ds, bIdx, mod, cutType, calDB, pars, verbose=True):
    """ Load cut data from the calDB and translate to TCut format.
    Used by: lat2.py, check-files.py
    """
    dsNum = int(ds[0]) if isinstance(ds, str) else int(ds)

    # load metadata and print a status message.
    det = DetInfo()
    chList = det.getGoodChanList(dsNum, mod)

    bkg = BkgInfo()
    bkgRanges = bkg.getRanges(ds)
    rFirst, rLast = bkgRanges[bIdx][0], bkgRanges[bIdx][-1]
    dsSub = ds if ds in ["5A","5B","5C"] else int(ds)
    subRanges = bkg.GetSubRanges(dsSub, bIdx) # this is finicky about int/str
    if len(subRanges) == 0: subRanges.append((rFirst, rLast))

    cal = CalInfo()
    calKey = "ds%d_m%d" % (dsNum, mod)
    if ds == "5C": calKey = "ds5c"
    if calKey not in cal.GetKeys(dsNum):
        print("Error: Unknown cal key:",calKey)
        return
    cIdxLo = cal.GetCalIdx(calKey, rFirst)
    cIdxHi = cal.GetCalIdx(calKey, rLast)
    nCal = cIdxHi+1 - cIdxLo

    if cutType == '-b': cutType = "th"
    if verbose: print("DS%d-M%d (%s) %s bIdx %d  (%d - %d)  nBkg %d  nCal %d" % (dsNum,mod,ds,cutType,bIdx,rFirst,rLast,len(subRanges),nCal))

    # -- 1. get data for cuts tuned by bkgIdx (thresholds) --
    # bkgDict = {ch:None for ch in chList}
    bkgDict = {}
    bkgCov = {ch:[] for ch in chList}
    for sIdx, (runLo, runHi) in enumerate(subRanges):

        bRunCut = "run>=%d && run<=%d" % (runLo, runHi)
        if verbose: print("  bIdx %d %d (%d - %d)" % (bIdx, sIdx, runLo, runHi))

        thD = getDBRecord("thresh_ds%d_bkg%d_sub%d" % (dsNum, bIdx, sIdx), False, calDB, pars)

        for ch in chList:

            if ch not in thD.keys():
                bkgCov[ch].append(0)
                continue

            # get threshold data for this bkg/sub/chan
            thrMu = thD[ch][0]
            thrSig = thD[ch][1]
            isBad = thD[ch][2]
            thrCut, chanCut = None, None
            if not isBad:
                thrCut = "trapENFCal>=%.2f " % (thrMu + 3*thrSig) # ***** 3 sigma threshold cut *****
                bkgCov[ch].append(1)
            else:
                bkgCov[ch].append(0)

            # create dict entry for this channel or append to existing, taking care of parentheses and OR's.
            chanCut = "(%s && %s)" % (bRunCut, thrCut) if len(subRanges) > 1 else thrCut

            if ch in bkgDict.keys() and thrCut!=None:
                bkgDict[ch] += " || %s" % chanCut
            elif ch not in bkgDict.keys() and thrCut!=None and len(subRanges) > 1:
                bkgDict[ch] = "(%s" % chanCut
            elif len(subRanges)==1 and thrCut != None:
                bkgDict[ch] = thrCut

    # close the parens for each channel entry
    for ch in bkgDict:
        if bkgDict[ch] is not None and len(subRanges) > 1:
            bkgDict[ch] += ")"

    # -- 2. get data for cuts tuned by calIdx (fitSlo, riseNoise)--
    calDict = {}
    calCov = {ch:[['fs'],['rn']] for ch in chList}
    for cIdx in range(cIdxLo, cIdxHi+1):
        runCovMin = cal.master[calKey][cIdx][1]
        runCovMax = cal.master[calKey][cIdx][2]
        runLo = rFirst if runCovMin < rFirst else runCovMin
        runHi = rLast if rLast < runCovMax else runCovMax
        cRunCut = "run>=%d && run<=%d" % (runLo, runHi)
        if verbose: print("  cIdx %d    (%d - %d)" % (cIdx, runLo, runHi))

        fsD = getDBRecord("fitSlo_%s_idx%d_m2s238" % (calKey, cIdx), False, calDB, pars)
        rnD = getDBRecord("riseNoise_%s_ci%d_pol" % (calKey, cIdx), False, calDB, pars)

        for ch in chList:

            # "fitSlo_[calKey]_idx[ci]_m2s238" : {ch : [fsCut, fs200] for ch in chList}}
            fsCut = None
            if fsD[ch] is not None and fsD[ch][0] > 0:
                fsCut = "fitSlo<%.2f" % fsD[ch][0]
                calCov[ch][0].append(1)
            else:
                calCov[ch][0].append(0)

            # "riseNoise_%s_ci%d_pol", "vals": {ch : [a,b,c99,c,fitPass] for ch in chList} }
            rnCut = None
            if rnD[ch] is not None and rnD[ch][3]!=False:
                a, b, c99, c, fitPass = rnD[ch]
                rnCut = "riseNoise < (%.2e*pow(trapENFCal,2) + %.2e*trapENFCal + %.3f)" % (a, b, c99)
                calCov[ch][1].append(1)
            else:
                calCov[ch][1].append(0)

            # set the combination channel cut
            chanCut = None
            if cutType == "fs" and fsCut!=None:
                chanCut = fsCut if nCal==1 else "(%s && %s)" % (cRunCut, fsCut)

            if cutType == "rn" and rnCut!=None:
                chanCut = rnCut if nCal==1 else "(%s && %s)" % (cRunCut, rnCut)

            if cutType == "fr" and fsCut!=None and rnCut!=None:
                chanCut = "%s && %s" % (fsCut, rnCut) if nCal==1 else "(%s && %s && %s)" % (cRunCut, fsCut, rnCut)

            # create dict entry for this channel or append to existing, taking care of parentheses and OR's.
            if ch in calDict.keys() and chanCut!=None:
                calDict[ch] += " || %s" % chanCut
            elif ch not in calDict.keys() and chanCut!=None:
                calDict[ch] = "(%s" % chanCut

    # close the parens for each channel entry
    for key in calDict:
        calDict[key] += ")"

    # final check
    # for ch in sorted(bkgDict):
        # print(ch, bkgDict[ch])

    # for ch in calDict:
        # print(ch, calDict[ch])

    return bkgDict, calDict, bkgCov, calCov


def test():
    print("testing...")

    cal = CalInfo()
    # runsCal = cal.GetSpecialList()
    # print(runsCal)

    bkg = BkgInfo()
    # print(bkg.dsMap())
    # print(bkg.dsRanges())
    # print(bkg.GetDSNum(18588))
    # print(bkg.GetBkgIdx(6,27065))
    # print(bkg.getRanges(4))

    det = DetInfo()
    # print("ds1", det.getChanList(1))
    # chan = det.getChanList(1)[0]
    # for ch in det.getChanList(1):
        # print(ch, det.getChanCPD(1,ch))
    # for ds in range(0,7):
        # goodChans = det.getGoodChanList(ds)
        # goodDets = det.getDetectorList(ds, goodChans)
        # print(goodDets)
    # det = DetInfo()
    # goodChans = det.getGoodChanList(2)
    # print(goodChans)

    # print(692, det.getChanCPD(0,692))
    # print(det.getPMon(ds=0))

    # ds = 1
    # run0 = bkg.getRunList(ds,42)[0]
    # print(det.getHVAtRun(ds,run0))
    # print(det.getHVAtRun(ds,run0,"chan")) # problematic
    # print(det.getTrapThreshAtRun(ds,run0))
    # th1 = det.getTrapThreshAtRun(ds,run0)
    # th2 = det.getTrapThreshAtRun(ds,14343)
    # hv1 = det.getHVAtRun(ds,run0)
    # hv2 = det.getHVAtRun(ds,14343)

    # verify that we pick up the change in p5d2
    # chanList = list(th1.keys())+list(th2.keys())
    # for cpd in sorted(det.allDetIDs):
    #     if cpd not in chanList: continue
    #     print("cpd %s run1: %d th %d hv %d , run2: %d th %d  hv %d" % (str(cpd),run0,th1[cpd],hv1[cpd],14343,th2[cpd],hv2[cpd]))

    # search the db
    # import tinydb as db
    # calDB = db.TinyDB("%s/calDB-v2.json" % latSWDir)
    # pars = db.Query()
    # recList = calDB.search(pars.key.matches("thresh"))
    # for idx in range(len(recList)):
        # key = recList[idx]['key']
        # vals = recList[idx]['vals']
        # print(key)

    # print(det.getPMon())
    # print(det.getCH())
    # for ds in det.getCH():
    #     print("DS",ds)
    #     for d in sorted(det.getCH(ds)):
    #         tmp = det.getCH(ds)[d]
    #         if len(tmp) > 0:
    #             print("cpd:",d, "(run,ch):", det.getCH(ds)[d])

    # now check the threshold and HV objects



if __name__=="__main__":
    test()
