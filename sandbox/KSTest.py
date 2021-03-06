#!/usr/bin/env python
import sys, time, os, ROOT
import numpy as np
from scipy.stats import ks_2samp
import seaborn as sns
import matplotlib.pyplot as plt
sns.set_style('darkgrid')

def main(argv):

    bUseBlind = True
    # dsList, module = [0,1,2,3,5,6], 1
    dsList, module = [1,2,3,5,6], 1
    # dsList, module = [4,5], 2
    # dsList, module = [6], 1

    # Channels across DS1, 2, 3, 5
    chList = [592, 608, 626, 632, 640, 648, 672, 690]
    # globalTime cut right now is because of some unrejected runs in blind DS1
    theCut = "isGood && !wfDCBits && !(isLNFill1 && C==1) && !(isLNFill2&&C==2) && isEnr && !muVeto && C=={}".format(module)
    # channelCut = "&& (channel=={}||channel=={}||channel=={}||channel=={}||channel=={}||channel=={}||channel=={}||channel=={})".format(*chList)
    channelCut = "&&((C==1&&P==1&&D==2)||(C==1&&P==1&&D==3)||(C==1&&P==1&&D==4)||(C==1&&P==2&&D==2)||(C==1&&P==2&&D==3)||(C==1&&P==3&&D==2)||(C==1&&P==3&&D==3)||(C==1&&P==3&&D==4)||(C==1&&P==5&&D==3)||(C==1&&P==6&&D==1)||(C==1&&P==6&&D==3)||(C==1&&P==6&&D==4)||(C==1&&P==7&&D==2)||(C==1&&P==7&&D==3)||(C==1&&P==7&&D==4))"

    # M1 Detectors across DS0-6
    # channelCut = "&&((C==1&&P==1&&D==2)||(C==1&&P==1&&D==3)||(C==1&&P==1&&D==4)||(C==1&&P==2&&D==2)||(C==1&&P==2&&D==3)||(C==1&&P==3&&D==4)||(C==1&&P==5&&D==3)||(C==1&&P==6&&D==3)||(C==1&&P==7&&D==2)||(C==1&&P==7&&D==3))"

    # channelCut = "&&((C==1&&P==1&&D==2)||(C==1&&P==1&&D==3)||(C==1&&P==1&&D==4)||(C==1&&P==2&&D==3)||(C==1&&P==3&&D==2)||(C==1&&P==3&&D==3)||(C==1&&P==3&&D==4)||(C==1&&P==5&&D==3)||(C==1&&P==6&&D==1)||(C==1&&P==7&&D==4))"
    # channelCut = "&&((C==1&&P==1&&D==2)||(C==1&&P==1&&D==3)||(C==1&&P==1&&D==4)||(C==1&&P==3&&D==2)||(C==1&&P==3&&D==4)||(C==1&&P==7&&D==2)||(C==1&&P==7&&D==3))"
    theCut += channelCut
    nuCut = theCut + " && mHL==1 && trapENFCalC>1000 && trapENFCalC<1400 && avse>-1 && dcr99<0"
    # dcrCut = theCut + " && mHL==1 && trapENFCalC>1950 && trapENFCalC<3350 && avse>-1 && dcr99>=0"
    # dcrCut = theCut + " && mHL==1 && trapENFCalC>1950 && trapENFCalC<3350 && avse>-1 && dcr99>=0"
    alphaCut = theCut + " && mHL==1 && trapENFCalC>4000 && trapENFCalC<8000 && avse>-1"
    dcrCut = theCut + " && mHL==1 && avse>-1 && ((trapENFCalC>1000 && trapENFCalC<5500 && dcr99>=0) || (dcr99<0 && trapENFCalC>2700 && trapENFCalC<5500)) "
    pbCut = theCut + " && mH==1 && trapENFCal>45.5 && trapENFCal<47.5"
    # excessCut = "C=={} && trapENFCal>2 && trapENFCal<5 || (channel!=656 && run < 6964)".format(module)
    excessCut = "C=={} && trapENFCal>2 && trapENFCal<5".format(module)

    h2nList = []
    halphaList = []
    pval = []

    sortnutot, pnutot = [], []
    sortalphatot, palphatot = [], []
    sortetot, petot = [], []
    sortpbtot, ppbtot = [], []
    sortexcesstot, pexcesstot = [], []
    ksresultTot, kseresultTot, kspbresultTot, ksexcessresultTot  = [], [], [], []
    endTime = []

    print ("Using cut for two nu: ", nuCut)
    print ("Using cut for alpha: ", alphaCut)
    print ("Using cut for dcr: ", dcrCut)
    print ("Using cut for pb: ", pbCut)
    print ("Using cut for low e: ", excessCut)

    for idx,ds in enumerate(dsList):
        print "Scanning dataset", ds
        skimOpen = ROOT.TChain("skimTree")
        skimCut = ROOT.TChain("skimTree")
        skimOpen.Add("/Users/brianzhu/project/skim/light/lightDS{}_open.root".format(ds))
        skimCut.Add("/Users/brianzhu/project/LATv2/bkg/cut/final95/final95_DS{}*.root".format(ds))
        if bUseBlind:
            skimOpen.Add("/Users/brianzhu/project/skim/light/lightDS{}_blind.root".format(ds))

        n2nu = skimOpen.Draw("globalTime", nuCut, "goff")
        nu = skimOpen.GetV1()
        nuList = list(int(nu[n]) for n in range(n2nu))

        nalpha = skimOpen.Draw("globalTime", alphaCut, "goff")
        alpha = skimOpen.GetV1()
        alphaList = list(int(alpha[n]) for n in range(nalpha))

        ne = skimOpen.Draw("globalTime", dcrCut, "goff")
        e = skimOpen.GetV1()
        eList = list(int(e[n]) for n in range(ne))

        npb = skimCut.Draw("globalTime", pbCut, "goff")
        pb = skimCut.GetV1()
        pbList = list(int(pb[n]) for n in range(npb))

        print('DS{} (1950 - 3350 keV) -- DCR Events: {}'.format(ds,ne))
        print('DS{} (4000 - 8000 keV) -- Alpha Events: {}'.format(ds,nalpha))
        print('DS{} (1000 - 1400 keV) -- 2nbb Events: {}'.format(ds,n2nu))
        print('DS{} (45.5 - 47.5 keV) -- Pb210 Events: {}'.format(ds,npb))

        if ds == 0:
            nexcess = skimCut.Draw("globalTime", excessCut + '&& channel!=656', "goff")
        else:
            nexcess = skimCut.Draw("globalTime", excessCut, "goff")
        excess = skimCut.GetV1()
        excessList = list(int(excess[n]) for n in range(nexcess))

        sortnu = np.sort(nuList)
        sortalpha = np.sort(alphaList)
        sorte = np.sort(eList)
        sortpb = np.sort(pbList)
        sortexcess = np.sort(excessList)

        pnu = 1. * np.arange(len(nuList)) / (len(nuList) - 1)
        palpha = 1. * np.arange(len(alphaList)) / (len(alphaList) - 1)
        pe = 1. * np.arange(len(eList)) / (len(eList) - 1)
        ppb = 1. * np.arange(len(pbList)) / (len(pbList) - 1)
        pexcess = 1. * np.arange(len(excessList)) / (len(excessList) - 1)

        ksresult = ks_2samp(nuList, alphaList)
        ksresultTot.append(ksresult)

        kseresult = ks_2samp(nuList, eList)
        kseresultTot.append(kseresult)

        kspbresult = ks_2samp(nuList, pbList)
        kspbresultTot.append(kspbresult)

        ksexcessresult = ks_2samp(nuList, excessList)
        ksexcessresultTot.append(ksexcessresult)

        # Save the ending time of each dataset (maximum time of last event of the 3 distributions)
        endTime.append( np.amax( [sortnu[-1], sorte[-1]] ) )

        sortnutot.extend(sortnu)
        pnutot.extend([x+idx for x in pnu])
        sortalphatot.extend(sortalpha)
        palphatot.extend([x+idx for x in palpha])
        sortetot.extend(sorte)
        petot.extend([x+idx for x in pe])
        sortpbtot.extend(sortpb)
        ppbtot.extend([x+idx for x in ppb])
        sortexcesstot.extend(sortexcess)
        pexcesstot.extend([x+idx for x in pexcess])

    # This is CDFs if we combine all of the datasets
    pnuSumTot = 1. * np.arange(len(sortnutot)) / (len(sortnutot) - 1)
    palphaSumTot = 1. * np.arange(len(sortalphatot)) / (len(sortalphatot) - 1)
    pdcrSumTot = 1. * np.arange(len(sortetot)) / (len(sortetot) - 1)
    ppbSumTot = 1. * np.arange(len(sortpbtot)) / (len(sortpbtot) - 1)
    pexcessSumTot = 1. * np.arange(len(sortexcesstot)) / (len(sortexcesstot) - 1)

    alphaSumResult = ks_2samp(sortnutot, sortalphatot)
    dcrSumResult = ks_2samp(sortnutot, sortetot)
    pbSumResult = ks_2samp(sortnutot, sortpbtot)
    excessSumResult = ks_2samp(sortnutot, sortexcesstot)

    ksTotResult = {'Alpha':alphaSumResult, 'DCR':dcrSumResult, 'Pb210':pbSumResult, 'Low E':excessSumResult}

    nuDate = np.asarray(sortnutot, dtype='datetime64[s]')
    alphaDate = np.asarray(sortalphatot, dtype='datetime64[s]')
    dcrDate = np.asarray(sortetot, dtype='datetime64[s]')
    pbDate = np.asarray(sortpbtot, dtype='datetime64[s]')
    excessDate = np.asarray(sortexcesstot, dtype='datetime64[s]')
    endDate = np.asarray(endTime, dtype='datetime64[s]')

    fig1, (a11, a12, a13, a14) = plt.subplots(nrows=4, figsize=(12,12))
    a11.step(nuDate, pnutot, color='green', label=r"$2\nu\beta\beta$")
    a11.step(alphaDate, palphatot, color='blue', label="Alphas (4-8 MeV)")
    a12.step(nuDate, pnutot, color='green', label=r"$2\nu\beta\beta$")
    a12.step(dcrDate, petot, color='blue', label="DCR rejected")
    a13.step(nuDate, pnutot, color='green', label=r"$2\nu\beta\beta$")
    a13.step(pbDate, ppbtot, color='blue', label="Pb210 (46 keV)")
    a14.step(nuDate, pnutot, color='green', label=r"$2\nu\beta\beta$")
    a14.step(excessDate, pexcesstot, color='blue', label="Low E (2 - 5 keV)")

    a11.set_xlabel("Date")
    a12.set_xlabel("Date")
    a13.set_xlabel("Date")
    a14.set_xlabel("Date")
    a11.set_ylabel("CDF")
    a12.set_ylabel("CDF")
    a13.set_ylabel("CDF")
    a14.set_ylabel("CDF")

    for idx, ds in enumerate(dsList[:-1]):
        a11.axvline(endDate[idx], color='red', alpha=0.5, linestyle=':')
        a12.axvline(endDate[idx], color='red', alpha=0.5, linestyle=':')
        a13.axvline(endDate[idx], color='red', alpha=0.5, linestyle=':')
        a14.axvline(endDate[idx], color='red', alpha=0.5, linestyle=':')
    a11.set_title("Module {} Eriched, All DS -- Alphas (4 - 8 MeV)".format(module))
    a12.set_title("Module {} Eriched, All DS -- DCR Rejected Alphas (2.35 - 3.35 MeV)".format(module))
    a13.set_title("Module {} Eriched, All DS -- Pb210 Gammas (45.5 - 47.5 keV)".format(module))
    a14.set_title("Module {} Eriched, All DS -- Low Energy (2 - 5 keV)".format(module))
    a11.legend(loc=4)
    labelText = ""
    for idx, ksres in enumerate(ksresultTot):
        labelText = labelText + "DS%d -- KS stat: %.3f   p-val: %.3f \n"%(dsList[idx], ksres[0], ksres[1])
    a11.text(0.05, 0.95, labelText, transform=a11.transAxes, fontsize=10, verticalalignment='top' )

    a12.legend(loc=4)
    labelText = ""
    for idx, ksres in enumerate(kseresultTot):
        labelText = labelText + "DS%d -- KS stat: %.3f   p-val: %.3f \n"%(dsList[idx], ksres[0], ksres[1])
    a12.text(0.05, 0.95, labelText, transform=a12.transAxes, fontsize=10, verticalalignment='top' )

    a13.legend(loc=4)
    labelText = ""
    for idx, ksres in enumerate(kspbresultTot):
        labelText = labelText + "DS%d -- KS stat: %.3f   p-val: %.3f \n"%(dsList[idx], ksres[0], ksres[1])
    a13.text(0.05, 0.95, labelText, transform=a13.transAxes, fontsize=10, verticalalignment='top' )

    a14.legend(loc=4)
    labelText = ""
    for idx, ksres in enumerate(ksexcessresultTot):
        labelText = labelText + "DS%d -- KS stat: %.3f   p-val: %.3f \n"%(dsList[idx], ksres[0], ksres[1])
    a14.text(0.05, 0.95, labelText, transform=a14.transAxes, fontsize=10, verticalalignment='top' )
    plt.tight_layout()
    # fig1.savefig('/Users/brianzhu/Desktop/KSTest_Pb210_M{}.png'.format(module))

    # On the same plot
    fig2, a2 = plt.subplots(figsize=(10,6))
    a2.step(nuDate, pnuSumTot, color = 'black', label=r"$2\nu\beta\beta$ (Clock)")
    # a2.step(alphaDate, palphaSumTot, label="Alphas (4-8 MeV)")
    a2.step(dcrDate, pdcrSumTot, label="Alpha Events")
    # a2.step(pbDate, ppbSumTot, label="Pb210 (46 keV)")
    # a2.step(excessDate, pexcessSumTot, label="Low E (2 - 5 keV)")
    # a2.set_title('Module {} Eriched, DS1-4,5bc'.format(module))
    a2.set_xlabel("Date")
    a2.set_ylabel("CDF")
    a2.legend(loc=4)
    for idx, ds in enumerate(dsList[:-1]):
        a2.axvline(endDate[idx], color='red', alpha=0.5, linestyle=':')

    labelText = ""
    for key, ksres in ksTotResult.items():
        if key != 'DCR': continue
        labelText = labelText + "{} -- KS statistic: {:.4f} -- p-value: {:.4f} \n".format(key, ksres[0], ksres[1])
    a2.text(0.05, 0.95, labelText, transform=a2.transAxes, fontsize=12, verticalalignment='top')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
	main(sys.argv[1:])
