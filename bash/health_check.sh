#!/bin/bash

##############################
## Author:Pushkar Narayan   ##
## Date: 08-31-2026         ##
##############################


############################################
# EC2 AUTO-HEALER
# Health Monitoring Script
############################################

NAMESPACE="EC2AutoHealer"

# Get Instance ID using IMDSv2
TOKEN=$(curl -s -X PUT \
    "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

INSTANCE_ID=$(curl -s \
    -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/instance-id)

echo "======================================"
echo "       EC2 AUTO-HEALER"
echo "======================================"
echo "Instance ID: $INSTANCE_ID"
echo "Time: $(date)"
echo "======================================"

############################################
# 1. CHECK NGINX
############################################

if systemctl is-active --quiet nginx
then
    NGINX_HEALTH=1
    echo "Nginx: HEALTHY"
else
    NGINX_HEALTH=0
    echo "Nginx: FAILED"
fi

############################################
# 2. CHECK DISK
############################################

DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')

echo "Disk Usage: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -lt 80 ]
then
    DISK_HEALTH=1
    echo "Disk: HEALTHY"
else
    DISK_HEALTH=0
    echo "Disk: WARNING"
fi

############################################
# 3. CHECK CPU
############################################

CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | \
    awk '{print 100 - $8}')

CPU_USAGE_INT=${CPU_USAGE%.*}

echo "CPU Usage: ${CPU_USAGE}%"

if [ "$CPU_USAGE_INT" -lt 90 ]
then
    CPU_HEALTH=1
    echo "CPU: HEALTHY"
else
    CPU_HEALTH=0
    echo "CPU: WARNING"
fi

############################################
# 4. OVERALL HEALTH
############################################

if [ "$NGINX_HEALTH" -eq 1 ] && \
   [ "$DISK_HEALTH" -eq 1 ] && \
   [ "$CPU_HEALTH" -eq 1 ]
then
    OVERALL_HEALTH=1
    echo "Overall Health: HEALTHY"
else
    OVERALL_HEALTH=0
    echo "Overall Health: FAILED"
fi

############################################
# 5. SEND METRICS TO CLOUDWATCH
############################################

aws cloudwatch put-metric-data \
    --namespace "$NAMESPACE" \
    --metric-name "NginxHealth" \
    --value "$NGINX_HEALTH" \
    --unit Count \
    --dimensions InstanceId="$INSTANCE_ID"

aws cloudwatch put-metric-data \
    --namespace "$NAMESPACE" \
    --metric-name "DiskHealth" \
    --value "$DISK_HEALTH" \
    --unit Count \
    --dimensions InstanceId="$INSTANCE_ID"

aws cloudwatch put-metric-data \
    --namespace "$NAMESPACE" \
    --metric-name "CPUHealth" \
    --value "$CPU_HEALTH" \
    --unit Count \
    --dimensions InstanceId="$INSTANCE_ID"

aws cloudwatch put-metric-data \
    --namespace "$NAMESPACE" \
    --metric-name "EC2Health" \
    --value "$OVERALL_HEALTH" \
    --unit Count \
    --dimensions InstanceId="$INSTANCE_ID"

aws cloudwatch put-metric-data \
    --namespace "$NAMESPACE" \
    --metric-name "DiskUsage" \
    --value "$DISK_USAGE" \
    --unit Percent \
    --dimensions InstanceId="$INSTANCE_ID"

aws cloudwatch put-metric-data \
    --namespace "$NAMESPACE" \
    --metric-name "CPUUsage" \
    --value "$CPU_USAGE" \
    --unit Percent \
    --dimensions InstanceId="$INSTANCE_ID"

echo "======================================"
echo "CloudWatch metrics published."
echo "======================================"