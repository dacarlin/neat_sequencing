# Neat Sequencing: dense multiplexed PacBio sequencing for synthetic biology

Neat sequencing is an idea that Justin Siegel (my PhD adviser at Davis) and I dreamed up as a way to use PacBio sequencing for enzyme design. A very brief motivation was that we wanted to replace our lab's current method of verifying designed DNA sequences. At the time, we were having to miniprep 20 µL of purified plasmid at a concentration greater that 10 ng/µL and ship it in two separate wells to a sequencing company to perform Sanger. Then, we had to either manually or using [some software I wrote](gs-checker) align two separate Sanger reads to a template and visually assess if the engineered changes we made to the DNA using Kunkel mutagenesis were present, or if the Gibson construct had mutations in it. 

Neat Sequencing solves a few of these problems if you are doing 100s of samples at a time. Briefly, it allows the use of Pacific Biosciences Single Molecule Real Time Sequencing to sequence up to 10,000 samples at one time, making the sequencing cost of each sample roughly $0.10. The method requires the purchase of a set of oligos (which can be reused for millions of samples) and a single PCR step. 

## Neat Sequencing workflow overview

### Sample prep 

There is none. You have your samples in a plate. Samples can be cells, glycerol stocks, purified DNA down to picograms per microliter. Basicially, anything that you can PCR. 

### Computational design of molecular barcodes

First, each sample needs to be associated with a unique molecular barcode. For this tutorial, we have 192 barcodes with adapter A, and 192 with adapter B. See notebook `barcode_scheme` for detailed barcoding scheme. 

### PCR-based assembly of barcoded amplicons

1. make master mix by cloning our barcode plate into PCR master mix
1. aliquot master mix
1. aliquot left primers 
1. aliquot right primers 
1. aliquot templates 

After LH, mix, seal, and spin down, put in thermal cycler. 

### Pooling

At this point, all samples are barcoded, so we can pool them. This can be achieved by the simple algorithm of pooling by row, then by column, into a single tube. Using multi-channel pipet or liquid handler encouraged. 

We recklessly pool everything in equal volume, or use crude A260 measurement to guide pooling. We do not use Qubit, because it is too expensive. 

### PacBio sequencing 

First, we do AMPure DNA cleanup. Next, SMRTbell template preparation for amplicons. Can de done by human in < 4 hours. To automate, consider the following steps: 

- Ligate adapters shipped as 20 μM oligonucleotide stock and are pre-annealed
- 30 µL DNA + 1 µL blunt adapter + buffer + 0.6 µL ligase (according to Yuko, works just as well as 1.0 µL) to final volume 40 µL.
- Incubate at 65 ˚C for 15 minutes–24 hours, storage for up to 24 hours at 4 c at this step, heat to 65 ˚C to inactivate ligase, and cool to 4 ˚C, immediately proceed to adding exo
-add 2 exos, 37 for 1 hour
-Size selection
-Use "Calculator" tool to set up primer binding
-Add primer, time?
-Bind polymerase to SMRTbell templates
-Add polymerase, 4 hours at 30 ˚C (Rita uses shorter time)
-Bind to beads
-Add beads
-Load into SMRTcell
-Optimal loading concentration 37% ZMW
-Load time is 30 minutes
-Plates are held at 4 ˚C until we have enough to continue

Run 10 hour movie on Sequel. For analysis, run both `CCS` and `LAA` pipelines. Unfortunately, the PacBio AMI is out of date, but it is relatively simple to launch EC2 instances 

### How to install PacBio SMRTLink on an AWS instance 

#### Launch and config an EC2 instance 

m3.2xlarge (8 CPUs, X GB ram, 2 x 80GB SSD instance storage) 

#### Copy your data files to the instance 

```bash
scp -r -i aws.pem data_files ec2-user@54.89.153.29:
#ok to leave in the ec2-user home dir for now 
```

#### Install SMRTLink 

First, download and unzip it 

```bash
curl -O https://downloads.pacbcloud.com/public/software/installers/smrtlink_4.0.0.190159.zip
unzip -P SmrT3chN smrtlink_4.0.0.190159.zip
```

Now you can install it right here (doesn't matter where) 

```bash
smrtlink_4.0.0.190159.run --rootDir smrtlink 
```

You will need to provide all the options. Most (all?) can be left as default. 

#### Run the consensus with barcoding 

To run analysis, I simply create small Bash scripts like this 

```
#!/bin/bash

SUBREADS=datafiles/5_E01/m54048_170422_091135.subreadset.xml
BARCODES=barcodes.fa

module load pb
pbsmrtpipe pipeline-id pbsmrtpipe.pipelines.sa3_ds_barcode_ccs -e eid_subread:$SUBREADS -e eid_barcode:$BARCODES
```
