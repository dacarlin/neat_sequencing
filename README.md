# Neat Sequencing: dense multiplexed PacBio sequencing for synthetic biology

Neat sequencing is an idea that Justin Siegel (my PhD adviser at Davis) and I dreamed up as a way to use PacBio sequencing for enzyme design. A very brief motivation was that we wanted to replace our lab's current method of verifying designed DNA sequences. At the time, we were having to miniprep 20 µL of purified plasmid at a concentration greater that 10 ng/µL and ship it in two separate wells to a sequencing company to perform Sanger. After receiving data in the form of chromatogram traces, the reads from the two wells have to be reassociated. Then, either manually or align the Sanger reads to the known template and visually (or automatically) assess if the engineered changes we made to the DNA using Kunkel mutagenesis were present, or if the Gibson construct had mutations in it. 

Some of this is scriptable (see [this attempt at automating Sanger verification](https://github.com/dacarlin/gs-checker)), but ultimately you end up looking at a lot of reads of medium quality. Neat Sequencing solves a few of these problems, provided **you are doing 100s of samples at a time** with read lengths above 700 bp. 

Briefly, the idea is to use a single Pacific Biosciences SMRTcell to sequence up to 10,000 multiplexed samples. This dramatically reduces the cost per sample compared to Sanger, and allows sequencing of up to 5,000 bp. The method requires the purchase of a set of oligos (which can be reused for millions of samples) and a single PCR step. 

When this may be useful:

- 100-10,000 samples
- each between 700 bp and 5 kb 
- diluted samples able to be be PCR template 

A more detailed overview of the method is as follows. For sample prep, dilute plasmids to about 1 ng/µL or less is fine. Whole cells can be used (touch a toothpick to colony and dip in PCR reaction). Choose a plate density appropriate to your application. Aliquot 10 µL (or less) of each sample to a well. Aliquot the barcodes. Aliquot the PCR master mix, run PCR, and pool the samples into a single tube. All of these operations should be performed using automated liquid handling (using Labcyte Echo 550 you can do 1 µL reactions). 

At this point, all samples are barcoded, so we can pool them. This can be achieved by the simple algorithm of pooling by row, then by column, into a single tube. Using multi-channel pipet or liquid handler, again, encouraged. We recklessly pool everything in equal volume, or use crude A260 measurement to guide pooling. We do not use Qubit, because it is too expensive.  

For the PacBio sequencing, first we do AMPure DNA cleanup. Next, SMRTbell template preparation for amplicons. Can de done by human in < 4 hours. Run 10 hour movie on Sequel. For analysis, run both `CCS` and `LAA` pipelines. Depending on your needs, you can look at the results from both. The PacBio secondary analysis is fairly compute-intensive, I would recommend not running on your laptop.  

## How to install PacBio SMRTLink on an AWS instance 

First, launch and config an EC2 instance. The m3.2xlarge with 300GB SSD seems to work well for data sets coming off the Sequel instrument. Copy your data files to the instance using your favorite method, for example: 

```bash
scp -r -i aws.pem data_files ec2-user@54.89.153.29:
```

Once your have your data files on the instance. Install PacBio SMRTlink. First, download and unzip it 

```bash
curl -O https://downloads.pacbcloud.com/public/software/installers/smrtlink_4.0.0.190159.zip
unzip -P SmrT3chN smrtlink_4.0.0.190159.zip
```

and install it right here (doesn't matter where) 

```bash
smrtlink_4.0.0.190159.run --rootDir smrtlink 
```

All the options can be left as default. 

## Run the consensus with barcoding 

To run analysis, I simply create small Bash scripts like this 

```
#!/bin/bash

SUBREADS=datafiles/5_E01/m54048_170422_091135.subreadset.xml
BARCODES=barcodes.fa

module load pb
pbsmrtpipe pipeline-id pbsmrtpipe.pipelines.sa3_ds_barcode_ccs -e eid_subread:$SUBREADS -e eid_barcode:$BARCODES
```

and run them with 

```bash 
bash sub.sh
``` 

