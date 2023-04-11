#!/bin/bash

extention=iso
mkdir tmp_$extention
rm -rf  scripts.iso
cp ProvisionGRUB.sh            tmp_$extention/provisiongrub.sh
cp RegenerateUUID.sh           tmp_$extention/regenerateuuid.sh
cp cron-cloud-install          tmp_$extention/
cp cloud-install               tmp_$extention/
cp cron-vz-guest-tools-install tmp_$extention/
cp vz-guest-tools              tmp_$extention/
cp vz-guest-tools-lin.tar      tmp_$extention/

mkisofs -o scripts.iso -r tmp_$extention/
rm -rf tmp_$extention
