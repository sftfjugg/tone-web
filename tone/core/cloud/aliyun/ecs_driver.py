import datetime
import logging
import time

import json

from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.DeleteInstanceRequest import DeleteInstanceRequest
from aliyunsdkecs.request.v20140526.DescribeAvailableResourceRequest import DescribeAvailableResourceRequest
from aliyunsdkecs.request.v20140526.DescribeDisksRequest import DescribeDisksRequest
from aliyunsdkecs.request.v20140526.DescribeImagesRequest import DescribeImagesRequest
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526.DescribeRegionsRequest import DescribeRegionsRequest
from aliyunsdkecs.request.v20140526.DescribeZonesRequest import DescribeZonesRequest
from aliyunsdkecs.request.v20140526.StopInstanceRequest import StopInstanceRequest

from tone.core.cloud.aliyun.base import BaseDriver
from tone.models import CloudAk

logger = logging.getLogger('aliyun')


class EcsDriver(BaseDriver):
    def __init__(self, access_id, access_key, region='cn-hangzhou', zone=None, resource_group_id=None):
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.zone = zone
        self.client = AcsClient(self.access_id, self.access_key, self.region)
        self.resource_group_id = resource_group_id

    def get_regions(self):
        try:
            request = DescribeRegionsRequest()
            response = self.client.do_action_with_exception(request)
            region_info_list = json.loads(response)['Regions']['Region']
            return [
                {
                    'name': item['LocalName'],
                    'id': item['RegionId'],
                    'endpoint': item['RegionEndpoint']
                }
                for item in region_info_list
            ]
        except Exception as e:
            logger.error('ecs sdk get_zones failed: {}'.format(str(e)))
            return []

    def get_zones(self, region=None):
        try:
            request = DescribeZonesRequest()
            response = self.client.do_action_with_exception(request)
            zone_info_list = json.loads(response)['Zones']['Zone']
            return [
                {
                    'name': item['LocalName'],
                    'id': item['ZoneId'],
                    'available_disk_categories': item['AvailableDiskCategories']['DiskCategories']
                }
                for item in zone_info_list
            ]
        except Exception as e:
            logger.error('ecs sdk get_zones failed: {}'.format(str(e)))
            return []

    def get_images(self, instance_type=None):
        try:
            request = DescribeImagesRequest()
            request.set_PageSize(100)
            if instance_type:
                request.set_InstanceType(instance_type)
            response = self.client.do_action_with_exception(request)
            images = json.loads(response)['Images']['Image']
            return [
                {
                    'id': item['ImageId'],
                    'name': item['ImageName'],
                    'platform': item['Platform'],
                    'owner_alias': item['ImageOwnerAlias']
                } for item in images
            ]
        except Exception as e:
            logger.error('ecs sdk get_images failed: {}'.format(str(e)))
            return []

    def show_instance_type(self, zone=None):
        try:
            request = DescribeAvailableResourceRequest()
            request.set_ZoneId(zone)
            request.set_DestinationResource('InstanceType')
            response = self.client.do_action_with_exception(request)
            available_zone = json.loads(response)['AvailableZones']['AvailableZone'][0]
            resources = available_zone['AvailableResources']['AvailableResource'][0]['SupportedResources'][
                'SupportedResource']
            return [
                {
                    'Status': item['Status'],
                    'Value': item['Value']
                }
                for item in resources
            ]
        except Exception as e:
            logger.error('ecs sdk show_instance_type failed: {}'.format(str(e)))
            return []

    def get_bandwidth(self, instance_id, region=None):
        try:
            instance = self.list_nodes(ex_node_ids=instance_id)
            if instance:
                bandwidth = instance[0].get('bandwidth')
            else:
                bandwidth = 0

        except Exception as e:
            bandwidth = 0
            logger.error('ecs sdk get_bandwidth failed: {}'.format(str(e)))
        return bandwidth

    def list_nodes(self, ex_node_ids=None, region=None, zone=None):
        try:
            request = DescribeInstancesRequest()
            request.set_PageSize(100)
            if zone:
                request.set_ZoneId(zone)
            if ex_node_ids:
                request.set_InstanceIds(ex_node_ids)
            if self.resource_group_id:
                request.set_ResourceGroupId(self.resource_group_id)
            response = self.client.do_action_with_exception(request)
            instances = json.loads(response)['Instances']['Instance']
            instance_list = []
            for instance in instances:
                instance_list.append(
                    {
                        'id': instance.get('InstanceId'),
                        'image': instance.get('ImageId'),
                        'name': instance.get('InstanceName'),
                        'hostname': instance.get('HostName'),
                        'private_ips': instance.get('VpcAttributes').get('PrivateIpAddress').get('IpAddress'),
                        'public_ips': instance.get('PublicIpAddress').get('IpAddress'),
                        'bandwidth': instance.get('InternetMaxBandwidthOut'),
                        'instance_type': instance.get('InstanceType'),
                        'serial_number': instance.get('SerialNumber'),
                        'extra': {
                            'expired_time': instance.get('ExpiredTime'),
                            'last_start_time': instance.get('StartTime'),
                            'eip_address': {'ip_address': instance.get('EipAddress')['IpAddress']}
                        }
                    }
                )
            return instance_list
        except Exception as e:
            logger.error('ecs sdk list_nodes failed: {}'.format(str(e)))
            return []

    def list_volumes(self, instance_id):
        try:
            request = DescribeDisksRequest()
            request.set_InstanceId(instance_id)
            if self.resource_group_id:
                request.set_ResourceGroupId(self.resource_group_id)
            response = self.client.do_action_with_exception(request)
            disks = json.loads(response)['Disks']['Disk']
            return [
                {
                    'size': disk.get('Size'),
                    'category': disk.get('Category'),
                }
                for disk in disks
            ]
        except Exception as e:
            logger.error('ecs sdk list_volumes failed: {}'.format(str(e)))
            return []

    def get_instance(self, instance_id, zone=None):
        try:
            instance = self.list_nodes([instance_id])
            if instance:
                instance_info = instance[0]
                disk_info = self.list_volumes(instance_id)
                disk_dict = dict(
                    data_disk_count=len(disk_info),
                    data_disk_size=disk_info[0]['size'],
                    data_disk_category=disk_info[0]['category']
                )
                return instance_info, disk_dict
            else:
                return None, None
        except Exception as e:
            logger.error('ecs sdk get_instance failed: {}'.format(str(e)))
            return None, None

    def get_instances(self, ex_node_ids=None, region=None, zone=None):
        try:
            nodes = self.list_nodes(ex_node_ids=ex_node_ids, region=zone, zone=zone)
            now = datetime.datetime.today()
            expired_format = '%Y-%m-%dT%H:%M%fZ'
            nodes = [i for i in nodes
                     if datetime.datetime.strptime(i['extra']['expired_time'], expired_format) > now]
            return nodes
        except Exception as e:
            logger.error('ecs sdk get_instances failed: {}'.format(str(e)))
            return None, None

    def stop_instance(self, instance_id):
        try:
            request = StopInstanceRequest()
            request.set_InstanceId(instance_id)
            response = self.client.do_action_with_exception(request)
            return json.loads(response)['RequestId']
        except Exception as e:
            logger.error('ecs sdk stop_instance failed: {}'.format(str(e)))
            return

    def delete_instance(self, instance_id):
        try:
            request = DeleteInstanceRequest()
            request.set_InstanceId(instance_id)
            response = self.client.do_action_with_exception(request)
            return True, json.loads(response)['RequestId']
        except Exception as e:
            if e.error_code == 'InvalidInstanceId.NotFound':
                # 机器实例之前已被释放
                return True, 'server has been released'
            logger.error('ecs sdk delete_instance failed: {}'.format(str(e)))
            return False, e.message

    def destroy_instance(self, instance_id, timeout=30):
        start_time = time.time()
        while time.time() - start_time < timeout:
            self.stop_instance(instance_id)
            success, msg = self.delete_instance(instance_id)
            if success:
                break
        else:
            return False, "释放机器失败：{}".format(msg)
        return True, msg
