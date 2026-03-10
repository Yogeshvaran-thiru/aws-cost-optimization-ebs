import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    DRY_RUN = True  # Set to False to actually delete snapshots
    PRICE_PER_GB = 0.05
    total_saved = 0

    # Get all EBS snapshots
    response = ec2.describe_snapshots(OwnerIds=['self'])

    # Get all active EC2 instance IDs
    instances_response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'stopped']}])
    active_instance_ids = set()

    for reservation in instances_response['Reservations']:
        for instance in reservation['Instances']:
            active_instance_ids.add(instance['InstanceId'])

    # Iterate through each snapshot and delete if it's not attached to any volume or the volume is not attached to a running instance
    for snapshot in response['Snapshots']:
        snapshot_id = snapshot['SnapshotId']
        volume_id = snapshot.get('VolumeId')
        snapshot_size = snapshot['VolumeSize']  # in GB
        snapshot_cost = snapshot_size * PRICE_PER_GB

        if not volume_id:
            # Delete the snapshot if it's not attached to any volume
            total_saved += snapshot_cost
            if DRY_RUN:
                print(f"[DRY-RUN] Would delete snapshot {snapshot_id} (not attached to any volume). Estimated savings: ${snapshot_cost:.2f}")
            else:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted snapshot {snapshot_id} (not attached to any volume). Saved approx. ${snapshot_cost:.2f}")
        else:
            # Check if the volume still exists
            try:
                volume_response = ec2.describe_volumes(VolumeIds=[volume_id])
                attachments = volume_response['Volumes'][0]['Attachments']
                # Volume exists but not attached to any running instance
                if not attachments:
                    total_saved += snapshot_cost
                    if DRY_RUN:
                        print(f"[DRY-RUN] Would delete snapshot {snapshot_id} (volume not attached to running instance). Estimated savings: ${snapshot_cost:.2f}")
                    else:
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        print(f"Deleted snapshot {snapshot_id} (volume not attached to running instance). Saved approx. ${snapshot_cost:.2f}")
            # Volume not found (possibly deleted)
            except ec2.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
                    total_saved += snapshot_cost
                    if DRY_RUN:
                        print(f"[DRY-RUN] Would delete snapshot {snapshot_id} (volume not found). Estimated savings: ${snapshot_cost:.2f}")
                    else:
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        print(f"Deleted snapshot {snapshot_id} (volume not found). Saved approx. ${snapshot_cost:.2f}")
    # Print total estimated savings
    # --------------------------
    print(f"Total estimated savings for this run: ${total_saved:.2f}")
