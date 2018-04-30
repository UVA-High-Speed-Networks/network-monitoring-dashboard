#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Apr  8 13:17:24 2018

@author: babraham
"""
import datetime
#code for type_mapper and dash_mapper taken from: https://github.com/Kitware/bat/blob/master/bat/bro_log_reader.py

# Setup the Bro to Python Type mapper
class BroDataConverter():
    def __init__(self):
        self.field_names = []
        self.field_types = []
        self.type_converters = []
        self.type_mapper = {'bool': lambda x: True if x == 'T' else False,
                            'count': int,
                            'int': int,
                            'double': float,
                            'time': lambda x: datetime.datetime.fromtimestamp(float(x)),
                            'interval': lambda x: datetime.timedelta(seconds=float(x)),
                            'string': lambda x: x,
                            'enum': lambda x: x,
                            'port': int,
                            'unknown': lambda x: x}
        self.dash_mapper = {'bool': False, 'count': 0, 'int': 0, 'port': 0, 'double': 0.0,
                            'time': datetime.datetime.fromtimestamp(86400), 'interval': datetime.timedelta(seconds=0),
                            'string': '-', 'unknown:': '-'}
        self.num_cols = ['resp_bytes', 'orig_bytes', 'resp_pkts', 'orig_pkts', 'duration', 'ts']
        self.calc_cols = ['intvl', 'flow_ct']
        self.id_cols = ['id.orig_h', 'id.resp_h', 'id.orig_p', 'id.resp_p', 'proto']
        self.flags = ['s','h','a','d','f','r','c','t','i','q']
        self.fkeys = self.flags + [f.upper() for f in self.flags]
        self.empty_flags = dict([(k, 0) for k in self.fkeys])
        self.metric_dict = {'src_bytes': 0,
                     'src_pkts': 0,
                     'dest_bytes': 0,
                     'dest_pkts': 0,
                     'intvl': 0, 
                     'duration': 0}
        self.base_fields = self.id_cols[:-1] + ['uid']
        self.fields = {}
        self.fields['conn'] = self.base_fields + ['orig_bytes', 'orig_pkts', 'proto', 'resp_bytes', 'resp_pkts', 'history', 'duration', 'service']
        self.fields['http'] = self.base_fields +  ['info_code','info_msg','method', 'orig_filenames','orig_mime_types','proxied','referrer','request_body_len','resp_filenames','response_body_len','status_code','status_msg','trans_depth','uri','user_agent','version']
        self.fields['dns'] = self.base_fields + ['AA','RA','RD','TC','TTLs','Z','answers','qclass','qclass_name','qtype','qtype_name','query','rcode','rcode_name','rejected','rtt','trans_id']
        self.fields['ssl'] = self.base_fields + ['cert_chain_fuids','cipher','client_cert_chain_fuids','client_issuer','client_subject','curve','established','issuer','last_alert','next_protocol','resumed','server_name','subject','validation_status','version']
        self.fields['smtp'] = self.base_fields + ['cc','date','first_received','from','helo','in_reply_to','is_webmail','last_reply','mailfrom','msg_id','path','rcptto','reply_to','subject','to','user_agent','x_originating_ip']
