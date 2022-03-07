import json
import logging
import time

from aliyunsdkcore.acs_exception.exceptions import ServerException, ClientException
from aliyunsdkcore.client import AcsClient
from aliyunsdkeci.request.v20180808 import DeleteContainerGroupRequest, DescribeContainerGroupsRequest
from aliyunsdkeci.request.v20180808.DescribeRegionsRequest import DescribeRegionsRequest

from tone.core.cloud.aliyun.aliyun_network import AliYunNetwork
from tone.core.cloud.aliyun.api_request import AliyunAPIRequest
from tone.core.cloud.aliyun.base import BaseDriver
from tone.core.cloud.aliyun.driver_lib import ExceptionHandler, AliYunException

logger = logging.getLogger('aliyun')


class EciDriver(BaseDriver):
    def __init__(self, access_id, access_key, region=None, zone=None):
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.zone = zone
        self.client = AcsClient(self.access_id, self.access_key, self.region)
        self.api_request = AliyunAPIRequest(self.access_id, self.access_key)

    def get_regions(self):
        try:
            response = self.api_request.get('DescribeRegions')
            response = json.loads(response)
            regions = response.get('Regions')
            return [
                {
                    'id': region.get('RegionId'),
                    'name': region.get('RegionId')
                }
                for region in regions
            ]
        except Exception as e:
            logger.error('eci sdk get_regions failed: {}'.format(str(e)))
            return []

    def get_zones(self):
        try:
            request = DescribeRegionsRequest()
            response = self.client.do_action_with_exception(request)
            region_info = json.loads(response).get('Regions')[0]
            return [
                {
                    'id': zone,
                    'name': zone
                }
                for zone in region_info.get('Zones')
            ]
        except Exception as e:
            logger.error('eci sdk get_zones failed: {}'.format(str(e)))
            return []

    def get_instances(self, region=None, zone=None):
        try:
            request = DescribeContainerGroupsRequest.DescribeContainerGroupsRequest()
            request.set_ZoneId(zone)
            response = self.client.do_action_with_exception(request)
            return json.loads(response)['ContainerGroups']
        except Exception as e:
            logger.error('eci sdk get_instances failed: {}'.format(str(e)))
            return None

    def get_instance(self, instance_id, zone):
        for instance in self.get_instances(zone=zone):
            if 'ContainerGroupId' in instance and instance['ContainerGroupId'] == instance_id:
                return instance, None
        return None, None

    def list_nodes(self, container_group_ids=None):
        try:
            request = DescribeContainerGroupsRequest.DescribeContainerGroupsRequest()
            if container_group_ids:
                if isinstance(container_group_ids, list):
                    request.set_ContainerGroupIds(json.dumps(container_group_ids))
                else:
                    raise AttributeError('container_group_ids should be a list of container group ids.')
            response = self.client.do_action_with_exception(request)
            response = json.loads(response)
            return response['ContainerGroups']
        except ServerException as e:
            ExceptionHandler.server_exception(e)
            raise AliYunException(msg=e.get_error_msg(), code=e.get_error_code(), request_id=e.get_request_id())
        except ClientException as e:
            ExceptionHandler.client_exception(e)
            raise AliYunException(msg=e.get_error_msg(), code=e.get_error_code())

    def describe_instance(self, instance_id):
        return self.list_nodes([instance_id])[0]

    def destroy_instance(self, container_group_id, timeout=300):
        node = self.describe_instance(container_group_id)
        eip_addr = node['InternetIp']
        try:
            request = DeleteContainerGroupRequest.DeleteContainerGroupRequest()
            request.set_ContainerGroupId(container_group_id)
            response = self.client.do_action_with_exception(request)
            start_time = time.time()
            while time.time() - start_time < timeout:
                nodes = self.list_nodes([container_group_id])
                if len(nodes) == 0:
                    break
            else:
                logger.error("eci destroy instance timeout, container_group_id is: {}".format(container_group_id))
            return response
        except ServerException as e:
            ExceptionHandler.server_exception(e)
            raise AliYunException(msg=e.get_error_msg(), code=e.get_error_code(), request_id=e.get_request_id())
        except ClientException as e:
            ExceptionHandler.client_exception(e)
            raise AliYunException(msg=e.get_error_msg(), code=e.get_error_code())
        finally:
            AliYunNetwork(self.access_id, self.access_key, self.region, self.zone).release_eip_address(eip_addr)

