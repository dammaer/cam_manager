#!/usr/bin/env python3
# coding=utf-8

# ======================= HIKVISION CAM SETUP ======================
'''
# Source of this module: https://github.com/qb60/hikvision-configure
# The repository provides tools for configuring Hikvision devices.
# Repository author: @qb60
'''

# 2023-10-04
# MAIN stream: /h264/ch1/main/av_stream
# SUB  stream: /mjpeg/ch1/sub/av_stream

# pip3 install --user pycryptodomex
# pip3 install --user requests
# OR
# /usr/bin/python3 -m pip install --user pycryptodomex
# /usr/bin/python3 -m pip install --user requests

device_name_prefix = 'PP'
time_zone_gmt_offset = '+5:00:00'
new_ntp = '10.10.10.10'

admin_user_name = 'admin'
# admin_old_password = 'qwer1234'
# admin_new_password = 'qwer1234'
# admin_new_password = admin_old_password

# additional users
# [username, password, permission]
# permission is
# 'n' - no video, no records
# 'v' - video, no records
# 'r' - video + records
# 'a' - all admin's permissions
# additional_users = [
#     ['monitoring', 'qwer1234', 'n'],
#     ['video', 'qwer1234', 'v'],
#     ['record', 'qwer1234', 'r'],
#     ['operator', 'qwer1234', 'a'],
# ]

# 1280,1920,2560,3072,3840,'max'
# 720, 1080,1440,1728,2160,'max'
# 1,2,4,6,8,10,12,15,16,18,20,22,25
# 'h265', 'h264', h265 fallbacks to h264 if not supported
main_stream_width = 'max'
main_stream_height = 'max'
main_stream_framerate = 15
main_stream_codec = 'h265'
main_stream_audio = True

# 320,640,640,704,'max'
# 240,360,480,576,'max'
# 1,2,4,6,8,10,12,15,16,18,20,22,25
# 'h265', 'h264', 'mjpeg', h265 fallbacks to h264 if not supported
sub_stream_width = 640
sub_stream_height = 480
sub_stream_framerate = 10
sub_stream_codec = 'mjpeg'
sub_stream_audio = False

wdr_on = False
wdr_level = 51

primary_dns = '5.5.5.5'
secondary_dns = '8.8.8.8'

sender_email = 'info@example.com'
sender_name_prefix = 'ip-cam-'
smtp_server = 'smtp.example.com'
notification_email1 = 'admin1@example.com'
notification_email2 = 'admin2@example.com'
notification_email3 = ''

reformat_sd_if_it_is_ok = True
photo_capture_interval_minutes = 5
video_ratio_percents = 99

# not less than 15s
DELAY_AFTER_FORMATTING_SECONDS = 20

# =============== DST ===============
# True False
enable_dst = False

# "00:30", "01:00", "01:30", "02:00"
dst_offset = "01:00"

# Start DST period
# 1..12
start_dst_month = 3

# 0 - sun, 1 - mon, ..., 6 - sat
start_dst_day_of_week = 3

# 1,2,3,4 - first, second, third or fourth, 5 - last
start_dst_day_order_number = 4

# 0..23
start_dst_hour = 0

# End DST period
end_dst_month = 9
end_dst_day_of_week = 3
end_dst_day_order_number = 4
end_dst_hour = 0
# ==================================


# ============================= MAIN WORK ===============================


def set_cam_options(auth_type, current_cam_ip, current_password, new_cam_ip):
    # UNCOMMENT NEEDED STEPS

    # set_additional_users(auth_type, current_cam_ip, current_password)
    # set_ntp(auth_type, current_cam_ip, current_password)
    # set_time(auth_type, current_cam_ip, current_password)
    # set_osd(auth_type, current_cam_ip, current_password)
    # set_off_ip_ban_option(auth_type, current_cam_ip, current_password)
    # set_video_streams(auth_type, current_cam_ip, current_password)
    # set_cloud_parameters(auth_type, current_cam_ip, current_password)
    # disable_unneeded_event_triggers(auth_type, current_cam_ip, current_password)
    # set_wdr(auth_type, current_cam_ip, current_password)

    # =========== for offices - motion detection and so on ===============
    set_integration_protocol_enabled(auth_type, current_cam_ip, current_password)
    add_onvif_user(auth_type, current_cam_ip, current_password, 'admin', current_password)
    set_basic_auth_method(auth_type, current_cam_ip, current_password)
    # set_device_name(auth_type, current_cam_ip, current_password, new_cam_ip)
    # set_email_notification_addresses(auth_type, current_cam_ip, current_password, new_cam_ip)
    # set_video_photo_ratio(auth_type, current_cam_ip, current_password)
    # set_motion_detector_parameters(auth_type, current_cam_ip, current_password)
    # format_storage(auth_type, current_cam_ip, current_password)
    # set_email_event_triggers(auth_type, current_cam_ip, current_password)
    # set_recording_by_motion_detector_trigger(auth_type, current_cam_ip, current_password)
    # set_recording_schedule(auth_type, current_cam_ip, current_password)
    # set_photo_capturing_parameters(auth_type, current_cam_ip, current_password)
    # ====================================================================

    # print_user_list(auth_type, current_cam_ip, current_password)
    # set_ip_and_dns(auth_type, current_cam_ip, new_cam_ip, current_password)
    # set_admin_password(auth_type, current_cam_ip, current_password, admin_new_password)
    # reboot_cam(auth_type, current_cam_ip, admin_password)
    pass


# ==================================================================

import re
import requests
import base64
import time
import sys
import ipaddress
from sys import stdout
from xml.etree import ElementTree
from requests.auth import HTTPDigestAuth
from requests.auth import HTTPBasicAuth
from Cryptodome.Cipher import AES
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5
from Cryptodome.Cipher.AES import MODE_ECB

# ==================================================================
VIDEO_TRACK_ID = '101'
PHOTO_TRACK_ID = '103'
# ============================= URLS ===============================

password_url = '/ISAPI/Security/users/1'
time_url = '/ISAPI/System/time'
ntp_url = '/ISAPI/System/time/ntpServers'
osd_url = '/ISAPI/System/Video/inputs/channels/1/overlays'
video_url = '/ISAPI/Streaming/channels'
video_capabilities_url = '/ISAPI/Streaming/channels/{}/capabilities'
wdr_url = '/ISAPI/Image/channels/1/WDR'
image_capabilities_url = '/ISAPI/Image/channels/1/capabilities'
ip_url = '/ISAPI/System/Network/interfaces/1/ipAddress'
reboot_url = '/ISAPI/System/reboot'
ip_ban_option_url = '/ISAPI/Security/illegalLoginLock'
network_capabilities_url = '/ISAPI/System/Network/capabilities'
cloud_url = '/ISAPI/System/Network/EZVIZ'
integration_protocol_url = '/ISAPI/System/Network/Integrate'

activation_status_url = '/SDK/activateStatus'
public_key_url = '/ISAPI/Security/challenge'
activation_url = '/ISAPI/System/activate'
users_url = '/ISAPI/Security/users'
onvif_users_url = '/ISAPI/Security/ONVIF/users'
permissons_url = '/ISAPI/Security/UserPermission'

device_info_url = '/ISAPI/System/deviceInfo'
email_addresses_url = '/ISAPI/System/Network/mailing/1'

event_diskfull_trigger_url = '/ISAPI/Event/triggers/diskfull/notifications'
event_diskerror_trigger_url = '/ISAPI/Event/triggers/diskerror/notifications'
event_motion_detector_trigger_url = '/ISAPI/Event/triggers/VMD-1/notifications'
event_trigger_base_url = '/ISAPI/Event/triggers/'

motion_detector_parameters_url = '/ISAPI/System/Video/inputs/channels/1/motionDetection'
recording_schedule_url = '/ISAPI/ContentMgmt/record/tracks/'
recording_video_schedule_url = recording_schedule_url + VIDEO_TRACK_ID
recording_photo_schedule_url = recording_schedule_url + PHOTO_TRACK_ID
shapshot_channel_url = '/ISAPI/Snapshot/channels/1'

video_photo_ratio_url = '/ISAPI/ContentMgmt/Storage/quota/1'

storages_status_url = '/ISAPI/ContentMgmt/Storage/hdd'
storage_format_url = '/ISAPI/ContentMgmt/Storage/hdd/1/format'
storage_format_percents_url = '/ISAPI/ContentMgmt/Storage/hdd/1/formatStatus'

security_capabilities_url = '/ISAPI/Security/capabilities'
web_authorization_type_url = '/ISAPI/Security/webCertificate'

# =========================== REQUESTS =============================

user_password_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<User>
    <id>id</id>
    <userName>name</userName>
    <password>pass</password>
    <userLevel>level</userLevel>
    <loginPassword>admin_pass</loginPassword>    
</User>
"""

add_user_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<User>
    <userName>video</userName>
    <userLevel>Viewer</userLevel>
    <password>pass</password>
    <userLevel>level</userLevel>
    <loginPassword>admin_pass</loginPassword>
</User>
"""

add_onvif_user_xml = """\
<?xml version="1.0" encoding="utf-8"?>
<UserList>
    <User>
        <id>0</id>
        <userName>admin</userName>
        <password>pass</password>
        <userType>administrator</userType>
    </User>
</UserList>
"""

time_zone_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<Time>
    <timeMode>NTP</timeMode>
    <timeZone>timezone</timeZone>
</Time>
"""

ntp_server_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<NTPServerList>
    <NTPServer>
        <id>1</id>
        <addressingFormatType>ipaddress</addressingFormatType>
        <ipAddress>1.1.1.1</ipAddress>
        <portNo>123</portNo>
        <synchronizeInterval>60</synchronizeInterval>
    </NTPServer>
</NTPServerList>
"""

ip_address_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<IPAddress>
<ipVersion>dual</ipVersion>
<addressingType>static</addressingType>
<ipAddress>address</ipAddress>
<subnetMask>255.255.255.0</subnetMask>
<ipv6Address>::</ipv6Address>
<bitMask>0</bitMask>
<DefaultGateway>
    <ipAddress>gateway</ipAddress>
    <ipv6Address>::</ipv6Address>
</DefaultGateway>
<PrimaryDNS>
    <ipAddress>8.8.8.8</ipAddress>
</PrimaryDNS>
<SecondaryDNS>
    <ipAddress>0.0.0.0</ipAddress>
</SecondaryDNS>
<Ipv6Mode>
    <ipV6AddressingType>ra</ipV6AddressingType>
    <ipv6AddressList>
        <v6Address>
            <id>1</id>
            <type>manual</type>
            <address>::</address>
            <bitMask>0</bitMask>
        </v6Address>
    </ipv6AddressList>
</Ipv6Mode>
</IPAddress>
"""

dhcp_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<IPAddress>
<ipVersion>dual</ipVersion>
<addressingType>dynamic</addressingType>
<ipAddress></ipAddress>
<subnetMask>255.255.255.0</subnetMask>
<ipv6Address>::</ipv6Address>
<bitMask>0</bitMask>
<Ipv6Mode>
    <ipV6AddressingType>ra</ipV6AddressingType>
    <ipv6AddressList>
        <v6Address>
            <id>1</id>
            <type>manual</type>
            <address>::</address>
            <bitMask>0</bitMask>
        </v6Address>
    </ipv6AddressList>
</Ipv6Mode>
</IPAddress>
"""

cloud_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<EZVIZ>
   <enabled>false</enabled>
</EZVIZ>
"""

# integration_protocol_xml = """\
# <?xml version="1.0" encoding="UTF-8"?>
# <Integrate>
#     <CGI>
#         <enable>true</enable>
#         <certificateType>digest/basic</certificateType>
#     </CGI>
# </Integrate>
# """

integration_protocol_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<Integrate>
    <ONVIF>
        <enable>true</enable>
        <certificateType/>
    </ONVIF>
</Integrate>
"""

osd_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<VideoOverlay>
    <normalizedScreenSize>
        <normalizedScreenWidth>704</normalizedScreenWidth>
        <normalizedScreenHeight>576</normalizedScreenHeight>
    </normalizedScreenSize>
    <attribute>
        <transparent>false</transparent>
        <flashing>false</flashing>
    </attribute>
    <fontSize>adaptive</fontSize>
    <TextOverlayList size="4"></TextOverlayList>
    <DateTimeOverlay>
        <enabled>true</enabled>
        <positionX>0</positionX>
        <positionY>544</positionY>
        <dateStyle>YYYY-MM-DD</dateStyle>
        <timeStyle>24hour</timeStyle>
        <displayWeek>false</displayWeek>
    </DateTimeOverlay>
    <channelNameOverlay>
        <enabled>false</enabled>
        <positionX>512</positionX>
        <positionY>64</positionY>
    </channelNameOverlay>
    <frontColorMode>auto</frontColorMode>
    <frontColor>000000</frontColor>
</VideoOverlay>
"""

ip_ban_option_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<IllegalLoginLock>
    <enabled>false</enabled>
</IllegalLoginLock>
"""

activation_password_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<ActivateInfo>
    <password>pass</password>
</ActivateInfo>
"""

public_key_xml = """\
<PublicKey>
    <key>publickey</key>
</PublicKey>
"""

device_info_xml = """\
<DeviceInfo version="2.0">
    <deviceName>name</deviceName>
</DeviceInfo>
"""

email_addresses_xml = """\
<mailing version="2.0">
    <id>1</id>
    <sender>
        <emailAddress></emailAddress>
        <name></name>
        <smtp>
            <enableAuthorization>false</enableAuthorization>
            <enableSSL>false</enableSSL>
            <addressingFormatType>hostname</addressingFormatType>
            <hostName></hostName>
            <portNo>25</portNo>
            <accountName></accountName>
            <enableTLS>false</enableTLS>
            <startTLS>false</startTLS>
        </smtp>
    </sender>
    <receiverList>
        <receiver>
            <id>1</id>
            <name></name>
            <emailAddress></emailAddress>
        </receiver>
        <receiver>
            <id>2</id>
            <name></name>
            <emailAddress></emailAddress>
        </receiver>
        <receiver>
            <id>3</id>
            <name></name>
            <emailAddress></emailAddress>
        </receiver>
    </receiverList>
    <attachment>
        <snapshot>
            <enabled>false</enabled>
            <interval>2</interval>
        </snapshot>
    </attachment>
</mailing>
"""

empty_event_trigger_xml = """\
<EventTriggerNotificationList version="2.0"></EventTriggerNotificationList>
"""

email_event_trigger_xml = """\
<EventTriggerNotificationList version="2.0">
    <EventTriggerNotification>
        <id>email</id>
        <notificationMethod>email</notificationMethod>
        <notificationRecurrence>beginning</notificationRecurrence>
    </EventTriggerNotification>
</EventTriggerNotificationList>
"""

recording_event_trigger_xml = """\
<EventTriggerNotificationList version="2.0">
    <EventTriggerNotification>
        <id>record-1</id>
        <notificationMethod>record</notificationMethod>
        <videoInputID>1</videoInputID>
        <notificationRecurrence>beginning</notificationRecurrence>
    </EventTriggerNotification>
</EventTriggerNotificationList>
"""

motion_detector_parameters_xml = """\
<MotionDetection version="2.0">
    <enabled>true</enabled>
    <enableHighlight>true</enableHighlight>
    <samplingInterval>2</samplingInterval>
    <startTriggerTime>500</startTriggerTime>
    <endTriggerTime>500</endTriggerTime>
    <regionType>grid</regionType>
    <Grid>
        <rowGranularity>18</rowGranularity>
        <columnGranularity>22</columnGranularity>
    </Grid>
    <MotionDetectionLayout version="2.0"
        xmlns="http://www.std-cgi.com/ver20/XMLSchema">
        <sensitivityLevel>20</sensitivityLevel>
        <layout>
            <gridMap>fffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffcfffffc</gridMap>
        </layout>
    </MotionDetectionLayout>
</MotionDetection>
"""

recording_schedule_time_xml = """\
<ScheduleBlock ScheduleActionSize="8" >
    <ScheduleBlockGUID>{00000000-0000-0000-0000-000000000000}</ScheduleBlockGUID>
    <ScheduleBlockType>www.std-cgi.com/racm/schedule/ver10</ScheduleBlockType>
    <ScheduleAction>
        <id>1</id>
        <ScheduleActionStartTime>
            <DayOfWeek>Monday</DayOfWeek>
            <TimeOfDay>00:00:00</TimeOfDay>
        </ScheduleActionStartTime>
        <ScheduleActionEndTime>
            <DayOfWeek>Monday</DayOfWeek>
            <TimeOfDay>24:00:00</TimeOfDay>
        </ScheduleActionEndTime>
        <ScheduleDSTEnable>false</ScheduleDSTEnable>
        <Description>nothing</Description>
        <Actions>
            <Record>true</Record>
            <ActionRecordingMode>MOTION</ActionRecordingMode>
        </Actions>
    </ScheduleAction>
    <ScheduleAction>
        <id>1</id>
        <ScheduleActionStartTime>
            <DayOfWeek>Tuesday</DayOfWeek>
            <TimeOfDay>00:00:00</TimeOfDay>
        </ScheduleActionStartTime>
        <ScheduleActionEndTime>
            <DayOfWeek>Tuesday</DayOfWeek>
            <TimeOfDay>24:00:00</TimeOfDay>
        </ScheduleActionEndTime>
        <ScheduleDSTEnable>false</ScheduleDSTEnable>
        <Description>nothing</Description>
        <Actions>
            <Record>true</Record>
            <ActionRecordingMode>MOTION</ActionRecordingMode>
        </Actions>
    </ScheduleAction>
    <ScheduleAction>
        <id>1</id>
        <ScheduleActionStartTime>
            <DayOfWeek>Wednesday</DayOfWeek>
            <TimeOfDay>00:00:00</TimeOfDay>
        </ScheduleActionStartTime>
        <ScheduleActionEndTime>
            <DayOfWeek>Wednesday</DayOfWeek>
            <TimeOfDay>24:00:00</TimeOfDay>
        </ScheduleActionEndTime>
        <ScheduleDSTEnable>false</ScheduleDSTEnable>
        <Description>nothing</Description>
        <Actions>
            <Record>true</Record>
            <ActionRecordingMode>MOTION</ActionRecordingMode>
        </Actions>
    </ScheduleAction>
    <ScheduleAction>
        <id>1</id>
        <ScheduleActionStartTime>
            <DayOfWeek>Thursday</DayOfWeek>
            <TimeOfDay>00:00:00</TimeOfDay>
        </ScheduleActionStartTime>
        <ScheduleActionEndTime>
            <DayOfWeek>Thursday</DayOfWeek>
            <TimeOfDay>24:00:00</TimeOfDay>
        </ScheduleActionEndTime>
        <ScheduleDSTEnable>false</ScheduleDSTEnable>
        <Description>nothing</Description>
        <Actions>
            <Record>true</Record>
            <ActionRecordingMode>MOTION</ActionRecordingMode>
        </Actions>
    </ScheduleAction>
    <ScheduleAction>
        <id>1</id>
        <ScheduleActionStartTime>
            <DayOfWeek>Friday</DayOfWeek>
            <TimeOfDay>00:00:00</TimeOfDay>
        </ScheduleActionStartTime>
        <ScheduleActionEndTime>
            <DayOfWeek>Friday</DayOfWeek>
            <TimeOfDay>24:00:00</TimeOfDay>
        </ScheduleActionEndTime>
        <ScheduleDSTEnable>false</ScheduleDSTEnable>
        <Description>nothing</Description>
        <Actions>
            <Record>true</Record>
            <ActionRecordingMode>MOTION</ActionRecordingMode>
        </Actions>
    </ScheduleAction>
    <ScheduleAction>
        <id>1</id>
        <ScheduleActionStartTime>
            <DayOfWeek>Saturday</DayOfWeek>
            <TimeOfDay>00:00:00</TimeOfDay>
        </ScheduleActionStartTime>
        <ScheduleActionEndTime>
            <DayOfWeek>Saturday</DayOfWeek>
            <TimeOfDay>24:00:00</TimeOfDay>
        </ScheduleActionEndTime>
        <ScheduleDSTEnable>false</ScheduleDSTEnable>
        <Description>nothing</Description>
        <Actions>
            <Record>true</Record>
            <ActionRecordingMode>MOTION</ActionRecordingMode>
        </Actions>
    </ScheduleAction>
    <ScheduleAction>
        <id>1</id>
        <ScheduleActionStartTime>
            <DayOfWeek>Sunday</DayOfWeek>
            <TimeOfDay>00:00:00</TimeOfDay>
        </ScheduleActionStartTime>
        <ScheduleActionEndTime>
            <DayOfWeek>Sunday</DayOfWeek>
            <TimeOfDay>24:00:00</TimeOfDay>
        </ScheduleActionEndTime>
        <ScheduleDSTEnable>false</ScheduleDSTEnable>
        <Description>nothing</Description>
        <Actions>
            <Record>true</Record>
            <ActionRecordingMode>MOTION</ActionRecordingMode>
        </Actions>
    </ScheduleAction>
</ScheduleBlock>
"""

recording_schedule_enabling_xml = """\
<CustomExtension>
    <CustomExtensionName>www.std-cgi.com/RaCM/trackExt/ver10</CustomExtensionName>
    <enableSchedule>true</enableSchedule>
    <PreRecordTimeSeconds>5</PreRecordTimeSeconds>
    <PostRecordTimeSeconds>5</PostRecordTimeSeconds>
</CustomExtension>
"""

video_photo_ratio_xml = """\
<diskQuota version="2.0">
    <id>1</id>
    <type>ratio</type>
    <videoQuotaRatio>100</videoQuotaRatio>
    <pictureQuotaRatio>0</pictureQuotaRatio>
</diskQuota>
"""


# ================================================== UTILS =================================================
class Enum:
    @classmethod
    def items(cls):
        return {f[0]: f[1] for f in cls.__dict__.items() if not f[0].startswith('__') and not callable(f[1]) and not hasattr(f[1], '__func__')}

    @classmethod
    def values(cls):
        return list(cls.items().values())


# ===========================================================================================================


class AuthType:
    BASIC = 1,
    DIGEST = 2,
    UNAUTHORISED = 3


def get_auth_type(cam_ip, password):
    request = requests.get(get_service_url(cam_ip, time_url), auth=HTTPBasicAuth(admin_user_name, password))
    if request.ok:
        return AuthType.BASIC

    request = requests.get(get_service_url(cam_ip, time_url), auth=HTTPDigestAuth(admin_user_name, password))
    if request.ok:
        return AuthType.DIGEST

    return AuthType.UNAUTHORISED


def get_auth(auth_type, name, password):
    if auth_type == AuthType.BASIC:
        return HTTPBasicAuth(name, password)
    elif auth_type == AuthType.DIGEST:
        return HTTPDigestAuth(name, password)
    else:
        return None


def get_service_url(cam_ip, relative_url):
    return 'http://' + cam_ip + relative_url


# =========================================== NTP =================================================


def set_ntp(auth_type, cam_ip, password):
    request = ElementTree.fromstring(ntp_server_xml)

    server_element = request.find('NTPServer')
    ip_element = server_element.find('ipAddress')
    ip_element.text = new_ntp

    request_data = ElementTree.tostring(request, encoding='utf8', method='xml')

    process_request(auth_type, cam_ip, ntp_url, password, request_data, 'NTP set')


# =========================================== IP & DNS =================================================


def set_ip_and_dns(auth_type, cam_ip, new_ip, password):
    if new_ip == DHCP_OPTION:
        enable_dhcp(auth_type, cam_ip, password)
        return

    if new_ip is not None:
        request = ElementTree.fromstring(ip_address_xml)

        new_ip_address = str(new_ip.ip)
        new_netmask = str(new_ip.netmask)
        new_gateway = str(next(new_ip.network.hosts()))

        ip_element = request.find('ipAddress')
        ip_element.text = new_ip_address

        net_mask_element = request.find('subnetMask')
        net_mask_element.text = new_netmask

        request = write_ip_to_xml(request, 'DefaultGateway', new_gateway)
        request = add_dns_to_xml(request)
        request_data = ElementTree.tostring(request, encoding='utf8', method='xml')

        message = 'IP set to %s, netmask %s, gateway %s, dns1 %s, dns2 %s' % (new_ip_address, new_netmask, new_gateway, primary_dns, secondary_dns)

        process_request(auth_type, cam_ip, ip_url, password, request_data, message, 'Reboot Required')
    else:
        print("New IP is not given, IP won't be changed")

    set_dns(auth_type, cam_ip, password)


def enable_dhcp(auth_type, cam_ip, password):
    process_request(auth_type, cam_ip, ip_url, password, dhcp_xml, 'DHCP enabled', 'Reboot Required')


def set_dns(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, ip_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)
    ip_address_info = ElementTree.fromstring(answer_text)

    addressing_type = ip_address_info.find('addressingType')
    if addressing_type is not None and addressing_type.text == 'static':
        ip_address_info = add_dns_to_xml(ip_address_info)
        request_data = ElementTree.tostring(ip_address_info, encoding='utf8', method='xml')

        process_request(auth_type, cam_ip, ip_url, password, request_data, 'DNS servers set')
    else:
        print("IP address is not static (DHCP, APIPA), DNS won't be set")


def add_dns_to_xml(xml):
    xml = write_ip_to_xml(xml, 'PrimaryDNS', primary_dns)
    xml = write_ip_to_xml(xml, 'SecondaryDNS', secondary_dns)
    return xml


def write_ip_to_xml(xml, tag_name, ip_value):
    parent_element = xml.find(tag_name)
    ip_element = parent_element.find('ipAddress')
    ip_element.text = ip_value
    return xml


# =========================================== VIDEO =================================================
MAXIMAL_RESOLUTION_OPTION = 'max'
DHCP_OPTION = 'dhcp'
FRAMERATE_MULTIPLIER = 100


class VideoCodecOptions(Enum):
    H264 = 'h264'
    H265 = 'h265'
    MJPEG = 'mjpeg'


class VideoCodec:
    H264 = 'H.264'
    H265 = 'H.265'
    MJPEG = 'MJPEG'


class WDRMode:
    ON = 'open'
    OFF = 'close'


class VideoMode:
    def __init__(self, width, height, framerate):
        self.width = width
        self.height = height
        self.framerate = framerate


class VideoCapabilities:
    def __init__(self, width_list, height_list, framerate_list, codec_list):
        self.width_list = width_list
        self.height_list = height_list
        self.framerate_list = framerate_list
        self.codec_list = codec_list

    def is_mode_supported(self, videomode):
        return self.width_list.count(videomode.width) != 0 \
               and self.height_list.count(videomode.height) != 0 \
               and self.framerate_list.count(videomode.framerate) != 0

    def is_codec_supported(self, codec):
        return self.codec_list.count(codec) != 0

    def get_maximal_resolution_mode(self, framerate):
        max_width = self.width_list[-1]
        max_height = self.height_list[-1]
        return VideoMode(max_width, max_height, framerate)


class ImageCapabilities:
    def __init__(self, wdr):
        self.wdr = wdr


class WDRCapabilities:
    def __init__(self, wdr_modes, wdr_level_range):
        self.wdr_modes = wdr_modes
        self.wdr_level_range = wdr_level_range

    def is_mode_supported(self, mode, level):
        (min_level, max_level) = self.wdr_level_range
        return self.wdr_modes.count(mode) != 0 and min_level <= level <= max_level


class VideoChannel:
    def __init__(self, name, stream_mode, codec, initial_video_xml_element, stream_audio):
        self.name = name
        self.stream_mode = stream_mode
        self.codec = codec
        self.initial_video_xml_element = initial_video_xml_element
        self.stream_audio = stream_audio

    def get_video_element(self):
        video_element = self.fill_video_element(self.initial_video_xml_element, self.stream_mode, self.codec)
        return video_element

    def fill_video_element(self, element, videomode, codec):
        width_element = element.find('videoResolutionWidth')
        width_element.text = str(videomode.width)

        height_element = element.find('videoResolutionHeight')
        height_element.text = str(videomode.height)

        frame_rate_element = element.find('maxFrameRate')
        frame_rate_element.text = str(videomode.framerate)

        codec_element = element.find('videoCodecType')
        codec_element.text = codec

        return element


def set_video_streams(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, video_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)
    channel_list = ElementTree.fromstring(answer_text)
    channels = channel_list.findall('StreamingChannel')
    is_mode_supported = True

    for channel in channels:
        channel_id = channel.find('id').text
        capabilities = get_video_capabilities(channel_id, auth_type, cam_ip, password)
        channel_video = channel.find('Video')
        if channel_id[-1:] == '1':
            video_mode = calculate_video_mode(main_stream_width, main_stream_height, main_stream_framerate, capabilities)
            codec = option_to_videocodec(main_stream_codec, capabilities)
            video_channel = VideoChannel('MAIN', video_mode, codec, channel_video, main_stream_audio)
        else:
            video_mode = calculate_video_mode(sub_stream_width, sub_stream_height, sub_stream_framerate, capabilities)
            codec = option_to_videocodec(sub_stream_codec, capabilities)
            video_channel = VideoChannel('SUB', video_mode, codec, channel_video, sub_stream_audio)

        audio_element = channel.find('Audio')
        if audio_element is not None:
            enabled_element = audio_element.find('enabled')
            enabled_element.text = 'true' if video_channel.stream_audio else 'false'

        print_video_mode_info(video_channel)

        if capabilities.is_mode_supported(video_channel.stream_mode):
            replace_subelement_with(channel, video_channel.get_video_element())
        else:
            is_mode_supported = False
            break

    if is_mode_supported:
        request_data = ElementTree.tostring(channel_list, encoding='utf8', method='xml')
        process_request(auth_type, cam_ip, video_url, password, request_data, 'Video streams set')
    else:
        print('VIDEO MODE IS NOT SUPPORTED BY CAMERA!')


def get_video_capabilities(channel_id, auth_type, cam_ip, password):
    request_url = video_capabilities_url.format(channel_id)
    request = requests.get(get_service_url(cam_ip, request_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)
    channel_capabilities = ElementTree.fromstring(answer_text)
    video_capabilities = channel_capabilities.find('Video')
    width_list = get_int_options_list(video_capabilities, 'videoResolutionWidth')
    height_list = get_int_options_list(video_capabilities, 'videoResolutionHeight')
    frame_rate_list = get_int_options_list(video_capabilities, 'maxFrameRate')
    codec_list = get_str_options_list(video_capabilities, 'videoCodecType')

    return VideoCapabilities(width_list, height_list, frame_rate_list, codec_list)


def calculate_video_mode(width, height, framerate, capabilities):
    if width == MAXIMAL_RESOLUTION_OPTION or height == MAXIMAL_RESOLUTION_OPTION:
        mode = capabilities.get_maximal_resolution_mode(framerate * FRAMERATE_MULTIPLIER)
    else:
        mode = VideoMode(width, height, framerate * FRAMERATE_MULTIPLIER)

    return mode


def get_str_options_list(element, tag):
    inner_element = element.find(tag)
    options_text = inner_element.attrib['opt']
    options = options_text.split(',')
    return options


def get_int_options_range(element, tag):
    inner_element = element.find(tag)
    min_value = inner_element.attrib['min']
    max_value = inner_element.attrib['max']
    return int(min_value), int(max_value)


def get_int_options_list(element, tag):
    options = get_str_options_list(element, tag)
    return list(map(int, options))


def option_to_videocodec(option, capabilities):
    if option == VideoCodecOptions.MJPEG:
        return VideoCodec.MJPEG

    if option == VideoCodecOptions.H265 and capabilities.is_codec_supported(VideoCodec.H265):
        return VideoCodec.H265

    return VideoCodec.H264


def print_video_mode_info(video_channel):
    mode = video_channel.stream_mode
    framerate = int(mode.framerate / FRAMERATE_MULTIPLIER)
    audio = 'AUDIO' if video_channel.stream_audio else 'NO AUDIO'
    print('Video stream: {} - {}/{} - {}x{}x{}'.format(video_channel.name, video_channel.codec, audio, mode.width, mode.height, framerate))


def set_wdr(auth_type, current_cam_ip, current_password):
    image_capabilities = get_image_capabilities(auth_type, current_cam_ip, current_password)

    if image_capabilities.wdr is None:
        print("WDR isn't available in this camera")
        return

    capabilities = image_capabilities.wdr

    wdr_mode = WDRMode.ON if wdr_on else WDRMode.OFF
    if not capabilities.is_mode_supported(wdr_mode, wdr_level):
        print('WDR SETTINGS (mode = {}, level = {}) ARE NOT SUPPORTED BY CAMERA!'.format(wdr_mode, wdr_level))
        return

    request = requests.get(get_service_url(current_cam_ip, wdr_url), auth=get_auth(auth_type, admin_user_name, current_password))
    answer_text = clear_xml_from_namespaces(request.text)
    wdr_element = ElementTree.fromstring(answer_text)

    wdr_mode_element = wdr_element.find('mode')
    wdr_mode_element.text = wdr_mode

    wdr_level_element = wdr_element.find('WDRLevel')
    wdr_level_element.text = str(wdr_level)

    request_data = ElementTree.tostring(wdr_element, encoding='utf8', method='xml')
    process_request(auth_type, current_cam_ip, wdr_url, current_password, request_data, 'WDR parameters set')


def get_image_capabilities(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, image_capabilities_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)
    image_capabilities_element = ElementTree.fromstring(answer_text)

    wdr_capabilities_element = image_capabilities_element.find('WDR')
    if wdr_capabilities_element is not None:
        wdr_modes = get_str_options_list(wdr_capabilities_element, 'mode')
        wdr_level_range = get_int_options_range(wdr_capabilities_element, 'WDRLevel')
        wdr_capabilities = WDRCapabilities(wdr_modes, wdr_level_range)
    else:
        wdr_capabilities = None

    return ImageCapabilities(wdr_capabilities)


# =========================================== REBOOT =================================================


def reboot_cam(auth_type, cam_ip, admin_password):
    request = requests.put(get_service_url(cam_ip, reboot_url), auth=get_auth(auth_type, admin_user_name, admin_password), data=[])
    answer_text = request.text

    print_answer_status('Reboot', answer_text, 'OK')


# =========================================== OSD =================================================

def set_osd(auth_type, cam_ip, password):
    process_request(auth_type, cam_ip, osd_url, password, osd_xml, 'OSD set')


# =========================================== IP BAN =================================================


def set_off_ip_ban_option(auth_type, cam_ip, password):
    if is_ip_ban_option_presented(auth_type, cam_ip, password):
        process_request(auth_type, cam_ip, ip_ban_option_url, password, ip_ban_option_xml, 'IP ban option unset')


def is_ip_ban_option_presented(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, ip_ban_option_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = request.text

    answer_xml = ElementTree.fromstring(answer_text)
    namespace = get_namespace(answer_xml)

    if answer_xml.tag == namespace + 'IllegalLoginLock':
        return True
    else:
        return False


# =========================================== CLOUD =================================================


def set_cloud_parameters(auth_type, cam_ip, password):
    if is_camera_supports(auth_type, cam_ip, password, network_capabilities_url, 'isSupportEZVIZ'):
        process_request(auth_type, cam_ip, cloud_url, password, cloud_xml, 'Cloud disabling')


# ========================================= INTEGRATION PROTOCOL ============================================

def set_integration_protocol_enabled(auth_type, cam_ip, password):
    if is_camera_supports(auth_type, cam_ip, password, network_capabilities_url, 'isSupportIntegrate'):
        process_request(auth_type, cam_ip, integration_protocol_url, password, integration_protocol_xml, 'Integration protocol enabling')


# =========================================== TIME =================================================

def set_time(auth_type, cam_ip, password):
    if timezone_has_right_format(time_zone_gmt_offset):
        camera_timezone = convert_gmt_offset_to_internal_timezone(time_zone_gmt_offset)

        if enable_dst:
            start_dst, end_dst = get_dst_params()
            camera_timezone += make_dst_string(dst_offset, start_dst, end_dst)

        request = ElementTree.fromstring(time_zone_xml)

        timezone_element = request.find('timeZone')
        timezone_element.text = camera_timezone

        request_data = ElementTree.tostring(request, encoding='utf8', method='xml')

        process_request(auth_type, cam_ip, time_url, password, request_data, 'Time set')

    else:
        print("Wrong timezone format")


def timezone_has_right_format(gmt_offset):
    format_matched = re.match(r'[+,-]?\d{1,2}:\d{2}:\d{2}', gmt_offset)
    return format_matched is not None


def convert_gmt_offset_to_internal_timezone(gmt_offset):
    prefix = 'CST'

    sign = gmt_offset[0]
    if sign == '-':
        suffix = '+' + gmt_offset[1:]
    elif sign == '+':
        suffix = '-' + gmt_offset[1:]
    else:
        suffix = '-' + gmt_offset

    return prefix + suffix


class DstParam:
    def __init__(self, month, day, day_order_number, hour):
        self.month = month
        self.day = day
        self.day_order_number = day_order_number
        self.hour = hour

    def __str__(self) -> str:
        return "Month: {}, Day: {}, Day number: {}, Hour: {}".format(self.month, self.day, self.day_order_number, self.hour)


def get_dst_params():
    start_dst = DstParam(month=start_dst_month, day=start_dst_day_of_week, day_order_number=start_dst_day_order_number, hour=start_dst_hour)
    end_dst = DstParam(month=end_dst_month, day=end_dst_day_of_week, day_order_number=end_dst_day_order_number, hour=end_dst_hour)
    return start_dst, end_dst


# DST01:30:00,M1.2.3/01:00:00,M4.5.6/04:00:00
def make_dst_string(offset, start_dst, end_dst):
    start = make_dst_part_string(start_dst)
    end = make_dst_part_string(end_dst)
    return "DST{}:00,{},{}".format(offset, start, end)


def make_dst_part_string(dst_param):
    return "M{}.{}.{}/{:02}:00:00".format(dst_param.month, dst_param.day_order_number, dst_param.day, dst_param.hour)


def dst_param_has_right_format(dst_param):
    is_month_valid = (1 <= dst_param.month <= 12)
    is_day_order_number_valid = (1 <= dst_param.day_order_number <= 5)
    is_day_valid = (0 <= dst_param.day <= 6)
    is_hour_valid = (0 <= dst_param.hour <= 23)

    return is_month_valid and is_day_order_number_valid and is_day_valid and is_hour_valid


def dst_offset_has_right_format(offset_string):
    proper_values = ["00:30", "01:00", "01:30", "02:00"]
    return offset_string in proper_values


# =========================================== ACTIVATION =================================================


def is_activated(cam_ip):
    request = requests.get(get_service_url(cam_ip, activation_status_url))
    answer_text = request.text

    answer_xml = ElementTree.fromstring(answer_text)
    namespace = get_namespace(answer_xml)

    answer_status_element = answer_xml.find(namespace + 'Activated')

    if answer_status_element is not None:
        status = answer_status_element.text
        if status == 'false':
            return False

    return True


def set_activation(cam_ip, admin_password):
    password = admin_password

    if not is_activated(cam_ip):
        private_key = RSA.generate(1024)

        answer = send_public_key(cam_ip, private_key)
        random_key_encrypted_text, answer_is_valid = extract_random_key_encrypted(answer)

        if answer_is_valid:
            random_key = decrypt_random_key(random_key_encrypted_text, private_key)
            pass_encrypted_encoded = encrypt_password(random_key, admin_password)
            process_activation_request(cam_ip, pass_encrypted_encoded, admin_password)
            password = admin_password

        else:
            print("Activation: error")
    else:
        print("Activation: cam is already activated or activation is not supported")

    return password


def send_public_key(cam_ip, private_key):
    public_key = private_key.publickey()
    public_key_bin = bytearray.fromhex('{:0192x}'.format(public_key.n))
    public_key_str = base64.b16encode(public_key_bin).lower()
    public_key_base64_encoded = base64.b64encode(public_key_str)

    request_xml = ElementTree.fromstring(public_key_xml)
    key_element = request_xml.find('key')
    key_element.text = public_key_base64_encoded.decode()

    request_data = ElementTree.tostring(request_xml, encoding='utf8', method='xml')

    request_xml = requests.post(get_service_url(cam_ip, public_key_url), data=request_data)
    answer_text = request_xml.text

    return answer_text


def extract_random_key_encrypted(answer):
    answer_xml = ElementTree.fromstring(answer)
    namespace = get_namespace(answer_xml)

    random_key_element = answer_xml.find(namespace + 'key')

    if random_key_element is not None:
        random_key_encrypted = random_key_element.text
        return random_key_encrypted, True

    else:
        return '', False


def decrypt_random_key(random_key_encrypted_text, private_key):
    random_key_encoded = base64.b64decode(random_key_encrypted_text)

    random_key_bin = base64.b16decode(random_key_encoded.upper())
    rsa = PKCS1_v1_5.new(private_key)
    random_key = rsa.decrypt(random_key_bin, sentinel=None)[-32:]

    return random_key


def encrypt_password(random_key_text, password):
    random_key = base64.b16decode(random_key_text.upper())
    first_part = random_key_text[:16]

    new_password_to_send = password.encode('ascii')
    new_password_to_send += bytearray(16 - len(new_password_to_send))

    aes = AES.new(random_key, MODE_ECB)
    pass_encrypted = aes.encrypt(first_part) + aes.encrypt(new_password_to_send)

    pass_encrypted_encoded = base64.b64encode(base64.b16encode(pass_encrypted).lower())

    return pass_encrypted_encoded


def process_activation_request(cam_ip, pass_encrypted_encoded, admin_password):
    request = ElementTree.fromstring(activation_password_xml)
    pass_element = request.find('password')
    pass_element.text = pass_encrypted_encoded.decode()

    request_data = ElementTree.tostring(request, encoding='utf8', method='xml')
    process_request(AuthType.UNAUTHORISED, cam_ip, activation_url, admin_password, request_data, 'Activation')


# ========================================= USER MANAGEMENT ===========================================================

class User:
    @classmethod
    def default(cls):
        return cls(0, "", "", False)

    def __init__(self, user_id, name, password, is_valid):
        self.id = user_id
        self.name = name
        self.password = password
        self.is_valid = is_valid


class UserPermissions(Enum):
    Nothing = 'n'
    Video = 'v'
    Records = 'r'
    All = 'a'


def user_level_for_permission(permission):
    if permission == UserPermissions.All:
        return 'Operator'
    else:
        return 'Viewer'


def print_user_list(auth_type, cam_ip, admin_password):
    request = requests.get(get_service_url(cam_ip, users_url), auth=get_auth(auth_type, admin_user_name, admin_password))
    answer_text = request.text

    answer_xml = ElementTree.fromstring(answer_text)
    namespace = get_namespace(answer_xml)

    user_elements = answer_xml.findall(namespace + 'User')

    users = []
    for user_element in user_elements:
        username_element = user_element.find(namespace + 'userName')
        if username_element is not None:
            username = username_element.text
            users.append(username)

    print('Users: {}'.format(users))


def set_admin_password(auth_type, cam_ip, current_password, new_password):
    user = User('1', 'admin', new_password, True)
    set_user_password_and_level(auth_type, cam_ip, current_password, user, 'Administrator')


def set_additional_users(auth_type, cam_ip, admin_password, additional_users):
    print('Adding users...')
    for user in additional_users:
        if len(user) == 3:
            username = user[0]
            user_password = user[1]
            permission = user[2]

            user_level = user_level_for_permission(permission)
            user = add_or_update_user(auth_type, cam_ip, admin_password, username, user_password, user_level)
            set_permissions(auth_type, cam_ip, admin_password, user, permission)
        else:
            print('WRONG user info "{}"!'.format(user))


def add_or_update_user(auth_type, cam_ip, admin_password, user_name, user_password, user_level):
    user = find_user(auth_type, cam_ip, admin_password, user_name)

    if user.is_valid:
        print("User '{}' is presented".format(user_name))
        user.password = user_password
        set_user_password_and_level(auth_type, cam_ip, admin_password, user, user_level)
        return user
    else:
        add_user(auth_type, cam_ip, admin_password, user_name, user_password, user_level)
        return find_user(auth_type, cam_ip, admin_password, user_name)


def set_user_password_and_level(auth_type, cam_ip, admin_password, user, user_level):
    user_element = ElementTree.fromstring(user_password_xml)

    user_element.find('id').text = user.id
    user_element.find('userName').text = user.name
    user_element.find('password').text = user.password
    user_element.find('loginPassword').text = admin_password
    user_element.find('userLevel').text = user_level

    request_text = ElementTree.tostring(user_element, encoding='utf8', method='xml')

    process_request(auth_type, cam_ip, users_url, admin_password, request_text, "'{}' user password updating".format(user.name))


def add_user(auth_type, cam_ip, admin_password, user_name, user_password, user_level):
    user_element = ElementTree.fromstring(add_user_xml)

    user_element.find('userName').text = user_name
    user_element.find('password').text = user_password
    user_element.find('loginPassword').text = admin_password
    user_element.find('userLevel').text = user_level

    request_text = ElementTree.tostring(user_element, encoding='utf8', method='xml')
    answer = requests.post(get_service_url(cam_ip, users_url), auth=get_auth(auth_type, admin_user_name, admin_password), data=request_text)

    answer_text = answer.text
    print_answer_status("Adding user '{}'".format(user_name), answer_text, 'OK')


def add_onvif_user(auth_type, cam_ip, admin_password, user_name, user_password):
    request = ElementTree.fromstring(add_onvif_user_xml)
    userlist_element = request.find('User')
    userlist_element.find('userName').text = user_name
    userlist_element.find('password').text = user_password

    request_text = ElementTree.tostring(request, encoding='utf8', method='xml')
    answer = requests.post(get_service_url(cam_ip, onvif_users_url), auth=get_auth(auth_type, admin_user_name, admin_password), data=request_text)

    answer_text = answer.text
    print_answer_status("Adding onfiv user '{}'".format(user_name), answer_text, 'OK')


def find_user(auth_type, cam_ip, admin_password, username):
    request = requests.get(get_service_url(cam_ip, users_url), auth=get_auth(auth_type, admin_user_name, admin_password))
    answer_text = request.text

    answer_xml = ElementTree.fromstring(answer_text)
    namespace = get_namespace(answer_xml)

    user_elements = answer_xml.findall(namespace + 'User')

    user = User.default()

    for user_element in user_elements:
        found_username_element = user_element.find(namespace + 'userName')

        if found_username_element is not None:
            found_username = found_username_element.text
            if found_username == username:
                user_id_element = user_element.find(namespace + 'id')
                if user_id_element is not None:
                    user = User(user_id_element.text, username, "", True)
                    break

    return user


def set_permissions(auth_type, cam_ip, admin_password, user, permission):
    permissions = find_video_permissions(auth_type, cam_ip, admin_password, user)
    permissions_id = permissions.find('id').text

    remote_permissions_element = permissions.find('remotePermission')

    if permission == UserPermissions.All:
        set_permission_recursive(remote_permissions_element)
    else:
        unset_permission_recursive(remote_permissions_element)

        channel_element = remote_permissions_element.find('videoChannelPermissionList').find('videoChannelPermission')

        if permission in [UserPermissions.Video, UserPermissions.Records]:
            preview_element = remote_permissions_element.find('preview')
            preview_element.text = 'true'
            preview_channel_element = channel_element.find('preview')
            preview_channel_element.text = 'true'

        if permission == UserPermissions.Records:
            playback_element = remote_permissions_element.find('playBack')
            playback_element.text = 'true'
            playback_channel_element = channel_element.find('playBack')
            playback_channel_element.text = 'true'

    request_text = ElementTree.tostring(permissions, encoding='utf8', method='xml')
    process_request(auth_type, cam_ip, permissons_url + '/' + permissions_id, admin_password, request_text, "'{}' user permissions updating".format(user.name))


def set_permission_recursive(element):
    for e in element:
        set_permission_recursive(e)

    if element.text == 'false':
        element.text = 'true'


def unset_permission_recursive(element):
    for e in element:
        unset_permission_recursive(e)

    if element.text == 'true':
        element.text = 'false'


def find_video_permissions(auth_type, cam_ip, admin_password, user):
    request = requests.get(get_service_url(cam_ip, permissons_url), auth=get_auth(auth_type, admin_user_name, admin_password))
    answer_text = request.text

    answer_xml = ElementTree.fromstring(clear_xml_from_namespaces(answer_text))
    permissions_elements = answer_xml.findall('UserPermission')

    for permission_element in permissions_elements:
        user_id_element = permission_element.find('userID')

        if user_id_element is not None:
            user_id = user_id_element.text
            if user_id == user.id:
                return permission_element

    return None


# =========================================== AUTHORIZATION =================================================


def set_basic_auth_method(auth_type, cam_ip, password):
    print('Enabling Basic authorization', end='')

    if auth_type != AuthType.BASIC:
        request = requests.get(get_service_url(cam_ip, security_capabilities_url), auth=get_auth(auth_type, admin_user_name, password))
        answer_text = clear_xml_from_namespaces(request.text)

        answer_xml = ElementTree.fromstring(answer_text)
        web_auth_types_capabilities_element = answer_xml.find('WebCertificateCap')

        if web_auth_types_capabilities_element is not None:
            auth_types = web_auth_types_capabilities_element.find('CertificateType').attrib['opt']

            if 'basic' in auth_types:
                enable_basic_auth(auth_type, cam_ip, password)
            else:
                print(': Basic authorization is not supported')
        else:
            print(': changing authorization is not supported')
    else:
        print(': authorization is already Basic')


def enable_basic_auth(auth_type, cam_ip, password):
    web_authorization_type_request = requests.get(get_service_url(cam_ip, web_authorization_type_url), auth=get_auth(auth_type, admin_user_name, password))
    web_authorization_type_text = clear_xml_from_namespaces(web_authorization_type_request.text)

    web_authorization_type_xml = ElementTree.fromstring(web_authorization_type_text)
    web_authorization_type_element = web_authorization_type_xml.find('CertificateType')
    web_authorization_type_element.text = 'digest/basic'

    request_text = ElementTree.tostring(web_authorization_type_xml, encoding='utf8', method='xml')
    process_request(auth_type, cam_ip, web_authorization_type_url, password, request_text, '')


# =========================================== DEVICE NAME =================================================


def set_device_name(auth_type, cam_ip, password, new_cam_ip):
    request = ElementTree.fromstring(device_info_xml)

    device_name_prefix_formatted = '{}-'.format(device_name_prefix) if device_name_prefix != '' else ''
    ip_for_device_name = choose_ip_for_information(cam_ip, new_cam_ip)
    device_name = '{}{}'.format(device_name_prefix_formatted, ip_for_device_name)

    device_name_element = request.find('deviceName')
    device_name_element.text = device_name

    request_data = ElementTree.tostring(request, encoding='utf8', method='xml')

    process_request(auth_type, cam_ip, device_info_url, password, request_data, 'Device name "{}" set'.format(device_name))


# =========================================== EMAIL NOTIFICATIONS ADDRESSES =================================================


def set_email_notification_addresses(auth_type, cam_ip, password, new_cam_ip):
    request = ElementTree.fromstring(email_addresses_xml)

    sender_element = request.find('sender')
    sender_element = set_email(sender_element, sender_email)

    sender_name_element = sender_element.find('name')
    sender_name_element.text = sender_name_prefix + choose_ip_for_information(cam_ip, new_cam_ip)

    set_smtp(sender_element)

    request = fill_receivers_email(request)

    request_data = ElementTree.tostring(request, encoding='utf8', method='xml')
    process_request(auth_type, cam_ip, email_addresses_url, password, request_data, 'Email notification addresses set')


def fill_receivers_email(parent_element):
    receiver_list_element = parent_element.find('receiverList')
    receiver_elements = receiver_list_element.findall('receiver')
    emails = [notification_email1, notification_email2, notification_email3]
    for receiver_element in receiver_elements:
        email_id_element = receiver_element.find('id')
        email_id = int(email_id_element.text) - 1
        email = emails[email_id]

        name_element = receiver_element.find('name')
        name_element.text = email

        set_email(receiver_element, email)
    return parent_element


def set_email(parent_element, email_value):
    sender_email_element = parent_element.find('emailAddress')
    sender_email_element.text = email_value
    return parent_element


def set_smtp(parent_element):
    smtp_element = parent_element.find('smtp')
    server_element = smtp_element.find('hostName')
    server_element.text = smtp_server
    return parent_element


# =========================================== EVENT TRIGGERS =================================================


def set_email_event_triggers(auth_type, cam_ip, password):
    process_request(auth_type, cam_ip, event_diskfull_trigger_url, password, email_event_trigger_xml, 'Email trigger for diskfull event set')
    process_request(auth_type, cam_ip, event_diskerror_trigger_url, password, email_event_trigger_xml, 'Email trigger for diskerror event set')


def set_recording_by_motion_detector_trigger(auth_type, cam_ip, password):
    process_request(auth_type, cam_ip, event_motion_detector_trigger_url, password, recording_event_trigger_xml, 'Recording by motion detector trigger set')


def disable_unneeded_event_triggers(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, event_trigger_base_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)

    supported_event_ids = mute_possible_events(answer_text)
    for event_id in supported_event_ids:
        target_url = event_trigger_base_url + event_id + '/notifications'
        process_request(auth_type, cam_ip, target_url, password, empty_event_trigger_xml, 'Event "{}" triggers disabling'.format(event_id))


def mute_possible_events(event_triggers_text):
    xml_event_triggers = ElementTree.fromstring(event_triggers_text)
    event_trigger_list = xml_event_triggers.find('EventTriggerList')

    events = []

    if event_trigger_list is not None:
        for event_trigger in event_trigger_list:
            id_element = event_trigger.find('id')
            if id_element is not None:
                id_text = id_element.text
                events.append(id_text)

    return events


# =========================================== MOTION DETECTOR =================================================


def set_motion_detector_parameters(auth_type, cam_ip, password):
    process_request(auth_type, cam_ip, motion_detector_parameters_url, password, motion_detector_parameters_xml, 'Motion detector parameters set')


# =========================================== RECORDING SCHEDULE =================================================


def set_recording_schedule(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, recording_video_schedule_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)
    track_element = ElementTree.fromstring(answer_text)
    track_element = replace_subelement_body_with_text(track_element, 'TrackSchedule', recording_schedule_time_xml)
    track_element = replace_subelement_body_with_text(track_element, 'CustomExtensionList', recording_schedule_enabling_xml)

    loop_enable_element = track_element.find('LoopEnable')
    loop_enable_element.text = "true"

    request_data = ElementTree.tostring(track_element, encoding='utf8', method='xml')
    process_request(auth_type, cam_ip, recording_video_schedule_url, password, request_data, 'Recording schedule set')


# ======================================= CAPTURING PHOTOS =================================================


def set_photo_capturing_parameters(auth_type, cam_ip, password):
    set_photo_schedule(auth_type, cam_ip, password)
    set_shapshot_settings(auth_type, cam_ip, password)


def set_photo_schedule(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, recording_photo_schedule_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)
    track_element = ElementTree.fromstring(answer_text)

    schedule_element = ElementTree.fromstring(recording_schedule_time_xml)
    actions = schedule_element.findall('ScheduleAction')

    for action in actions:
        recording_mode = action.find('Actions').find('ActionRecordingMode')
        recording_mode.text = 'CMR'

    recording_schedule_enabling_element = ElementTree.fromstring(recording_schedule_enabling_xml)

    pre_record_time_element = recording_schedule_enabling_element.find('PreRecordTimeSeconds')
    pre_record_time_element.text = '0'

    post_record_time_element = recording_schedule_enabling_element.find('PostRecordTimeSeconds')
    post_record_time_element.text = '0'

    track_element = replace_subelement_body_with(track_element, 'TrackSchedule', schedule_element)
    track_element = replace_subelement_body_with(track_element, 'CustomExtensionList', recording_schedule_enabling_element)

    loop_enable_element = track_element.find('LoopEnable')
    loop_enable_element.text = "false"

    request_data = ElementTree.tostring(track_element, encoding='utf8', method='xml')
    process_request(auth_type, cam_ip, recording_photo_schedule_url, password, request_data, 'Photo capture schedule set')


def set_shapshot_settings(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, shapshot_channel_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)
    shapshot_channel_element = ElementTree.fromstring(answer_text)

    timing_capture_element = shapshot_channel_element.find('timingCapture')
    timing_capture_element.find('enabled').text = 'true'

    compress_element = timing_capture_element.find('compress')
    compress_element.find('quality').text = '80'
    compress_element.find('captureInterval').text = str(photo_capture_interval_minutes * 60000)

    request_data = ElementTree.tostring(shapshot_channel_element, encoding='utf8', method='xml')
    process_request(auth_type, cam_ip, shapshot_channel_url, password, request_data, 'Photo capture enabling')


# =========================================== STORAGE =================================================

class StorageStatus:
    OK = 'ok'
    UNFORMATTED = 'unformatted'
    FORMATTING = 'formatting'
    NOT_FOUND = 'not found'
    ERROR = 'error'
    UNKNOWN = 'unknown'


class FormattingStatus:
    FORMATTING = 0,
    NOT_FORMATTING = 1,
    ERROR = 2


def set_video_photo_ratio(auth_type, cam_ip, password):
    ratio_elements = ElementTree.fromstring(video_photo_ratio_xml)
    photo_ratio_percents = 100 - video_ratio_percents
    ratio_elements.find('videoQuotaRatio').text = str(video_ratio_percents)
    ratio_elements.find('pictureQuotaRatio').text = str(photo_ratio_percents)

    request_data = ElementTree.tostring(ratio_elements, encoding='utf8', method='xml')
    message = 'Video-photo ratio (video: {}%, photo: {}%) set'.format(video_ratio_percents, photo_ratio_percents)

    process_request(auth_type, cam_ip, video_photo_ratio_url, password, request_data, message)


def format_storage(auth_type, cam_ip, password):
    print("Format storage")
    authenticator = get_auth(auth_type, admin_user_name, password)
    storage_status = get_storage_status(authenticator, cam_ip)
    storage_capacity = get_storage_capacity(authenticator, cam_ip)
    print_storage_status_and_capacity(storage_status, storage_capacity)

    if storage_status == StorageStatus.NOT_FOUND:
        print("THERE'S NO STORAGE FOR FORMATTING!")
        return

    if storage_status == StorageStatus.OK:
        print("Storage is already formatted{}".format(": reformatting" if reformat_sd_if_it_is_ok else ""))

    if storage_status != StorageStatus.OK or reformat_sd_if_it_is_ok:
        do_format_storage(authenticator, cam_ip)


def get_storage_capacity(authenticator, cam_ip):
    storages_list = requests.get(get_service_url(cam_ip, storages_status_url), auth=authenticator)
    storages_list_text = clear_xml_from_namespaces(storages_list.text)

    storages_list_element = ElementTree.fromstring(storages_list_text)
    hdd_element = storages_list_element.find('hdd')

    if hdd_element is not None:
        status_element = hdd_element.find('capacity')
        capacity = int(status_element.text) / 1024.0
        return capacity

    else:
        return 0


def get_storage_status(authenticator, cam_ip):
    storages_list = requests.get(get_service_url(cam_ip, storages_status_url), auth=authenticator)
    storages_list_text = clear_xml_from_namespaces(storages_list.text)

    storages_list_element = ElementTree.fromstring(storages_list_text)
    hdd_element = storages_list_element.find('hdd')

    if hdd_element is None:
        return StorageStatus.NOT_FOUND
    else:
        status_element = hdd_element.find('status')

        status_table = {
            'ok': StorageStatus.OK,
            'unformatted': StorageStatus.UNFORMATTED,
            'formating': StorageStatus.FORMATTING,
            'error': StorageStatus.ERROR
        }

        return status_table.get(status_element.text, StorageStatus.UNKNOWN)


def print_storage_status_and_capacity(status_text, capacity):
    print('Storage size ~{} GB, status: {}'.format(capacity, status_text))


def do_format_storage(authenticator, cam_ip):
    # unformatted
    # formatting 0%
    # ...
    # formatting 88%
    # ok
    # not found
    # ... 15 seconds
    # ok

    start_formatting(authenticator, cam_ip)
    time.sleep(1)

    display_formatting_process(authenticator, cam_ip)
    time.sleep(DELAY_AFTER_FORMATTING_SECONDS)

    percentage = get_formatting_percentage(authenticator, cam_ip)
    storage_status = get_storage_status(authenticator, cam_ip)

    if storage_status == StorageStatus.OK:
        print('\rFormatting: {}%         Status: {}                 '.format(percentage, storage_status))
        print('Formatting: success')
    else:
        print('')
        raise RuntimeError('ERROR during formatting, storage status: {}'.format(storage_status))


def start_formatting(authenticator, cam_ip):
    try:
        requests.put(get_service_url(cam_ip, storage_format_url), auth=authenticator, timeout=1)
    except requests.exceptions.RequestException:
        pass


def display_formatting_process(authenticator, cam_ip):
    prev_percentage = 0

    while True:
        percentage = get_formatting_percentage(authenticator, cam_ip)
        storage_status = get_storage_status(authenticator, cam_ip)

        if storage_status != StorageStatus.FORMATTING:
            break

        if percentage != prev_percentage:
            stdout.write('\rFormatting: {}%         Status: {}                 '.format(percentage, storage_status))
            stdout.flush()
        prev_percentage = percentage

        time.sleep(1)


def get_formatting_percentage(authenticator, cam_ip):
    percents_answer = requests.get(get_service_url(cam_ip, storage_format_percents_url), auth=authenticator)

    if percents_answer:
        percents_answer_text = clear_xml_from_namespaces(percents_answer.text)
        percents_element = ElementTree.fromstring(percents_answer_text)

        percentage = percents_element.find('percent')
        return percentage.text
    else:
        return 0


# =========================================== VARIOUS STUFF =================================================

def is_camera_supports(auth_type, cam_ip, password, capabilities_url, property_name):
    request = requests.get(get_service_url(cam_ip, capabilities_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)

    answer_xml = ElementTree.fromstring(answer_text)
    property_element = answer_xml.find(property_name)

    if property_element is not None:
        if property_element.text == 'true':
            return True

    return False


def print_device_info(auth_type, cam_ip, password):
    request = requests.get(get_service_url(cam_ip, device_info_url), auth=get_auth(auth_type, admin_user_name, password))
    answer_text = clear_xml_from_namespaces(request.text)
    device_info = ElementTree.fromstring(answer_text.encode('utf-8'))

    model = device_info.find('model').text
    mac = device_info.find('macAddress').text
    fw_version = device_info.find('firmwareVersion').text

    print('MAC: {}, Model: {}, Firmware {}'.format(mac.upper(), model, fw_version))


def choose_ip_for_information(current_ip, new_cam_ip):
    if new_cam_ip == DHCP_OPTION:
        return DHCP_OPTION
    elif new_cam_ip is not None:
        return str(new_cam_ip.ip)
    else:
        return current_ip


def process_request(auth_type, cam_ip, request_url, password, request_data, operation, expected_status_text='OK'):
    request = requests.put(get_service_url(cam_ip, request_url), auth=get_auth(auth_type, admin_user_name, password), data=request_data)
    answer_text = request.text

    print_answer_status(operation, answer_text, expected_status_text)


def print_answer_status(operation_text, answer_text, status_text):
    default_status_text = 'OK'
    answer_xml = ElementTree.fromstring(answer_text)
    namespace = get_namespace(answer_xml)

    answer_status_element = answer_xml.find(namespace + 'statusString')

    result_status = False
    if answer_status_element is not None:
        status = answer_status_element.text
        if (status == status_text) or (status == default_status_text):
            result_status = True

    if result_status:
        print(operation_text + ': success')
    else:
        error_answer = parse_error_xml(answer_text)
        error_message = operation_text + ' error, answer is:\n' + error_answer
        print(answer_text)
        raise RuntimeError(error_message)


def parse_error_xml(answer_text):
    answer_xml = ElementTree.fromstring(answer_text)
    namespace = get_namespace(answer_xml)

    answer_status_element = answer_xml.find(namespace + 'statusString')
    answer_substatus_element = answer_xml.find(namespace + 'subStatusCode')

    if answer_status_element is not None and answer_substatus_element is not None:
        status = answer_status_element.text
        substatus = answer_substatus_element.text

        message = "%s: %s" % (status, substatus)

    else:
        message = answer_text

    return message


def get_namespace(element):
    m = re.match(r'{.*}', element.tag)
    return m.group(0) if m else ''


def clear_xml_from_namespaces(xml_text):
    return re.sub(r' xmlns="[^"]+"', '', xml_text, count=0)


def replace_subelement_with(parent, new_subelement):
    subelement_tag = new_subelement.tag
    subelement = parent.find(subelement_tag)
    parent.remove(subelement)
    parent.append(new_subelement)
    return parent


def replace_subelement_body_with_text(parent, subelement_tag, new_body_text):
    new_body = ElementTree.fromstring(new_body_text)
    return replace_subelement_body_with(parent, subelement_tag, new_body)


def replace_subelement_body_with(parent, subelement_tag, new_body):
    subelement = parent.find(subelement_tag)
    subelement.clear()
    subelement.append(new_body)
    return parent


# ====================================== CHECKING PARAMETERS ================================================
def check_parameters():
    check_admin_password()
    check_users_info(additional_users)
    check_dst()
    check_video_modes()


def check_admin_password(admin_password):
    print('Checking admin password...')
    check_user_password(admin_password, 'Wrong admin_new_password')


def check_user_password(password, message):
    if password == '':
        raise RuntimeError('{}, password is empty'.format(message))

    if len(password) < 8:
        raise RuntimeError('{}, password is too short, 8 symbols required'.format(message))


def check_users_info(users):
    print('Checking additional users info...')

    for user in users:
        if len(user) == 3:
            username = user[0]
            if username == '':
                raise RuntimeError('Wrong user info: {}, name is empty'.format(user))

            password = user[1]
            check_user_password(password, 'Wrong user info: {}'.format(user))

            user_level = user[2]
            if user_level not in UserPermissions.values():
                permissions = ["'{}'".format(p) for p in UserPermissions.values()]
                raise RuntimeError("User '{}' has wrong permission '{}', only {} are allowed".format(username, user_level, ",".join(permissions)))
        else:
            raise RuntimeError('Wrong user info: {}, not enough parameters'.format(user))


def check_dst():
    if enable_dst:
        print('Checking DST parameters...')

        if not dst_offset_has_right_format(dst_offset):
            raise RuntimeError("DST offset {} is not suitable".format(dst_offset))

        start_dst, end_dst = get_dst_params()
        is_start_param_valid = dst_param_has_right_format(start_dst)
        is_end_param_valid = dst_param_has_right_format(end_dst)

        message_template = "Wrong {} DST parameter: {}"

        if not is_start_param_valid:
            raise RuntimeError(message_template.format("start", start_dst))

        if not is_end_param_valid:
            raise RuntimeError(message_template.format("end", end_dst))


def check_video_modes():
    print('Checking video modes...')
    check_video_mode('main', main_stream_width, main_stream_height, main_stream_codec, [VideoCodecOptions.H264, VideoCodecOptions.H265])
    check_video_mode('sub', sub_stream_width, sub_stream_height, sub_stream_codec, VideoCodecOptions.values())


def check_video_mode(channel_name, width, height, codec, available_codecs):
    if is_resolution_wrong(width) or is_resolution_wrong(height):
        raise RuntimeError('Wrong resolution for {} stream: {} x {}'.format(channel_name, width, height))

    if codec not in available_codecs:
        raise RuntimeError('Wrong video codec for {} stream: {}'.format(channel_name, codec))


def is_resolution_wrong(resolution):
    return isinstance(resolution, str) and resolution != MAXIMAL_RESOLUTION_OPTION


# ===========================================================================================================
class CommandLineOptions:
    def __init__(self, current_ip, new_ip):
        self.current_ip = current_ip
        self.new_ip = new_ip


def parse_command_line_arguments(args):
    current_ip = args[1]
    if len(args) == 3:
        ip_or_dhcp = args[2]
        if ip_or_dhcp.lower() == DHCP_OPTION:
            new_ip = DHCP_OPTION
        else:
            new_ip = parse_ip(ip_or_dhcp)
    else:
        new_ip = None

    return CommandLineOptions(current_ip, new_ip)


def parse_ip(ip_with_mask):
    if ip_with_mask.count('/') == 0:
        ip_with_mask += '/24'

    return ipaddress.ip_interface(str(ip_with_mask))


def main():
    if len(sys.argv) > 1:
        options = parse_command_line_arguments(sys.argv)

        print('Processing cam %s:' % options.current_ip)

        try:
            check_parameters()

            current_password = set_activation(options.current_ip)
            auth_type = get_auth_type(options.current_ip, current_password)
            if auth_type == AuthType.UNAUTHORISED:
                raise RuntimeError("Unauthorised! Check login and password")

            print_device_info(auth_type, options.current_ip, current_password)
            set_cam_options(auth_type, options.current_ip, current_password, options.new_ip)

        except RuntimeError as e:
            print(e)

        except requests.exceptions.ConnectionError as e:
            print('Connection error: %s' % e)

        except KeyboardInterrupt:
            pass
    else:
        print("USAGE:")
        print("    {} OLD_IP [NEW_IP/MASK]".format(sys.argv[0]))
        print("    {} OLD_IP [dhcp]".format(sys.argv[0]))
        print()
        print("Examples:")
        print("    {} 10.10.10.10".format(sys.argv[0]))
        print("    {} 10.10.10.10 10.10.11.10".format(sys.argv[0]))
        print("    {} 10.10.10.10 dhcp".format(sys.argv[0]))

    print("")


def activate(host, password, additional_users):
    current_password = set_activation(host, password)
    auth_type = get_auth_type(host, current_password)
    if auth_type == AuthType.UNAUTHORISED:
        raise RuntimeError("Unauthorised! Check login and password")
    set_cam_options(auth_type, host, current_password, host)
    set_additional_users(auth_type, host, current_password, additional_users)


if __name__ == "__main__":
    activate('192.168.1.64', 'newpassword')
