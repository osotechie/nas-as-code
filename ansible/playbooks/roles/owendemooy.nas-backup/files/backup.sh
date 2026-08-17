#!/bin/bash
#Purpose = Backup Docker Container Data
#Version 1.0
#START

LVM_VG=ubuntu-vg		         				# Define name of the LVM Group to create snapshot from
LVM_LV=$LVM_VG/ubuntu-lv                 		# Define name of the LVM Volume to create snapshot from
SNAPSHOT=BACKUP                          		# Name for the Snapshot (note: cannot use SNAPSHOT as resevered word)
SNAPSHOT_SIZE=100G			 					# Size to allocate for Snapshot
SNAPSHOT_DEV=/dev/$LVM_VG/$SNAPSHOT 	 		# Device path to the snapshot
SNAPSHOT_MNT=/mnt/backup/snapshot	 			# Mount point for the snapshot

SRC_DIR=/docker                           		# Location of Data to be backed up
DES_DIR=/mnt/storage/backups/nas-repo       	# Destination of backup file
STACKS=/config/stacks			 				# Define path to dir containing subdirs for each docker stack

export RESTIC_PASSWORD=

echo $(date)'   Starting Backup'
echo $(date)'   -----------------------------------------------------------------------------------'

#Stop Docker Containers to allow clean backup
echo $(date)'    Stopping Container'
for dir in $STACKS/*/; do
	cd "$dir"
	docker compose stop
	cd ..
done

#Create Snapshot to backup data from
echo $(date)'    Creating Snapshot'
lvcreate -s -n $SNAPSHOT -L $SNAPSHOT_SIZE $LVM_LV
mount $SNAPSHOT_DEV $SNAPSHOT_MNT

#Re-start Docker Containers now we have a snapshot to work from
for dir in $STACKS/*/; do
	cd "$dir"
	docker compose up -d
	cd ..
done

#Bounce Traefik after the herd start to fix the docker/file provider startup race
#(routers reference Real-IP@file before the file provider loads it -> 404s until restarted).
#A lone restart re-loads routes against a settled container set. See Argus / issue traefik#9779.
echo $(date)'    Settling for 20s then restarting Traefik to rebuild route table'
sleep 20
docker restart Traefik


#Backup data
echo $(date)'    Backing up persistant data for Containers from snapshot'
echo restic -r $DES_DIR --verbose backup $SRC_DIR
restic -r $DES_DIR --verbose backup $SRC_DIR

#Remove snapshot
echo $(date)'    Removing Snapshot'
umount $SNAPSHOT_MNT
lvremove $LVM_VG/$SNAPSHOT -f

#Cleanup old restic backups
echo $(date)'    Cleaning up old backups (keeping last 7 daily, 4 weekly, 12 monthly)'
echo restic -r $DES_DIR forget --prune --keep-daily 7 --keep-weekly 4 --keep-monthly 12 
restic -r $DES_DIR forget --prune --keep-daily 7 --keep-weekly 4 --keep-monthly 12 

#END