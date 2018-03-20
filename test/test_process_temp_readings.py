import process_temp_readings

from datetime import *
import copy
import io
import json
import sys
import time

import botocore.errorfactory

from unittest.mock import *

def test_read_config():
    mock_xenv = Mock()
    mock_xenv.s3 = Mock()
    cfg = dict(minimum_temperature = 42, repeat_alert_hours = 3, phonenumber = "lololo", max_delay = 10)
    mock_xenv.s3.get_object.return_value = dict(Body = io.StringIO(json.dumps(cfg)))
    rcfg = process_temp_readings.read_config(mock_xenv)
    for k in [ky for ky in cfg.keys() if not ky == 'max_delay']:
        assert rcfg.__getattribute__(k) == cfg[k]
    assert rcfg.max_delay == 600

def test_Status():
    st = process_temp_readings.Status(100.01, 123456)
    assert st.temp_reading == 100.01
    assert st.last_reading_ts == 123456
    assert st.last_alert_ts == 0
    assert st.create_json() == '{"temperature_reading": 100.01, "last_reading_timestamp": 123456, "last_alert_timestamp": 0}'
    strf = io.StringIO('{"temperature_reading":10.234,"last_reading_timestamp":1000000001,"last_alert_timestamp":123456}')
    st2 = process_temp_readings.Status.read_status(strf)
    assert st2.temp_reading == 10.234
    assert st2.last_reading_ts == 1000000001
    assert st2.last_alert_ts == 123456
    
def print_readings(rdgs):
    for r in rdgs:
        ts = datetime.fromtimestamp(r['timestamp'])
        tmp = r['temperature']
        if 'received' in r:
            rc = datetime.fromtimestamp(r['received'])
            print('timestamp: {:%Y%m%d %H:%M:%S}, temperature: {}, received: {:%Y%m%d %H:%M:%S}'.format(ts, tmp, rc))
        else:
            print('timestamp: {:%Y%m%d %H:%M:%S}, temperature: {}'.format(ts, tmp))

def test_slit_by_date():
    basets = datetime(2018,2,1,12,33,44,123456)
    oneday = timedelta(days=1)
    onehour = timedelta(seconds=3600)
    oneone = timedelta(seconds=3660)
    readings = [dict(timestamp=x.timestamp(), temperature=y, received=z) \
                for x,y,z in ((basets, 12.5, basets + oneone), (basets + oneday, 8.78, basets + oneone), (basets + onehour, 33.0, basets + oneone))]
    res = process_temp_readings.split_by_date(readings)
    keys = res.keys()
    assert len(keys) == 2
    assert frozenset(keys) == frozenset((date(2018,2,1), date(2018,2,2)))
    assert readings[0] in res[date(2018,2,1)]
    assert readings[2] in res[date(2018,2,1)]
    assert res[date(2018,2,2)] == [readings[1]]

    
def test_write_readings():
    xenv = Mock()
    xenv.s3 = Mock()
    xenv.s3.get_object = Mock()
    received = datetime(2018,3,8,23,23,59).timestamp()
    ts11 = datetime(2018,3,8,22,33,44)
    ts12 = ts11 + timedelta(seconds=600)
    ts13 = ts11 + timedelta(seconds=1200)
    ts21 = datetime(2018,3,9,1,2,3)
    ts22 = ts21 + timedelta(seconds=600)
    ts23 = ts21 + timedelta(seconds=1200)
    rdgs1 = [dict(timestamp=ts11.timestamp(), temperature=1, received=received),
             dict(timestamp=ts12.timestamp(), temperature=2, received=received),
             dict(timestamp=ts13.timestamp(), temperature=3, received=received)]
    rdgs2 = [dict(timestamp=ts21.timestamp(), temperature=10, received=received),
             dict(timestamp=ts22.timestamp(), temperature=20, received=received),
             dict(timestamp=ts23.timestamp(), temperature=30, received=received)]
    datemaps = dict()
    datemaps[ts11.date()] = rdgs1
    datemaps[ts21.date()] = rdgs2
    exstrdgs = [dict(timestamp=(ts11 + timedelta(seconds=60)).timestamp(), temperature=0, received=datetime(2018,3,8,21,1,9).timestamp()),
                dict(timestamp=(ts11 + timedelta(seconds=900)).timestamp(), temperature=7, received=datetime(2018,3,8,21,1,9).timestamp())]
    def get_object(Bucket, Key):
        if Key == 'allreadings/day20180308.json':
            return dict(Body=io.StringIO(json.dumps(exstrdgs)))
        elif Key == 'allreadings/day20180309.json':
            raise botocore.errorfactory.ClientError({}, 'test')
        else:
            raise Exception('Unexpected key in mock get_object(): ' + Key)
    xenv.s3.get_object.side_effect = get_object
    process_temp_readings.write_readings(xenv, 'eimer', datemaps)
    assert xenv.s3.put_object.call_count == 2
    print('\n1')
    print_readings(json.loads(xenv.s3.put_object.mock_calls[0][2]['Body']))
    print('2')
    print_readings(json.loads(xenv.s3.put_object.mock_calls[1][2]['Body']))
    act_readings1 = json.loads(xenv.s3.put_object.mock_calls[0][2]['Body'])
    assert act_readings1 == [rdgs1[0], exstrdgs[0], rdgs1[1], exstrdgs[1], rdgs1[2]]
    act_readings2 = json.loads(xenv.s3.put_object.mock_calls[1][2]['Body'])
    assert act_readings2 == rdgs2
    
    
def test_consolidate_readings():
    received = datetime(2018,3,8,23,23,59).timestamp()
    ts11 = datetime(2018,3,8,22,33,44)
    ts12 = ts11 + timedelta(seconds=600)
    ts13 = ts11 + timedelta(seconds=1200)
    rdgs1 = [dict(timestamp=ts11.timestamp(), temperature=1, received=received),
             dict(timestamp=ts12.timestamp(), temperature=2, received=received),
             dict(timestamp=ts13.timestamp(), temperature=3, received=received)]
    assert process_temp_readings.consolidate_readings([rdgs1[0]]) == [rdgs1[0]]
    trdgs = list(reversed([rdgs1[0], rdgs1[1], rdgs1[0], rdgs1[1], rdgs1[2], rdgs1[0], rdgs1[2]]))
    assert process_temp_readings.consolidate_readings(trdgs) == rdgs1
    
    
def test_process_temperature_reading():
    ts11 = datetime(2018,3,8,22,33,44)
    ts12 = ts11 + timedelta(seconds=600)
    ts13 = ts11 + timedelta(seconds=1200)
    rdgs1 = [dict(timestamp=ts11.timestamp(), temperature=5),
             dict(timestamp=ts12.timestamp(), temperature=4),
             dict(timestamp=ts13.timestamp(), temperature=3)]
    s3data = dict(bucket = dict(name='eimer'), object=dict(key='s3objectkey'))
    event = dict(eventSource='aws:s3', s3=s3data)
    events = [event, event]
    xenv = Mock()
    xenv.s3 = Mock()
    jsonrdgs = json.dumps(rdgs1)
    xenv.s3.get_object.side_effect = [dict(Body=io.StringIO(jsonrdgs), ContentLength=len(jsonrdgs)), dict(Body=io.StringIO(jsonrdgs), ContentLength=len(jsonrdgs))]
    xenv.config = Mock()
    xenv.config.minimum_temperature = 3
    xenv.config.max_delay = 3
    xenv.config.repeat_alert_hours = 3    
    xenv.last_status.last_alert_ts = 42
    xenv.last_status.temp_reading = None
    xenv.last_reading_ts = None
    currenttime = ts13.timestamp() + 10
    consdict = dict()
    rdgswithts = [copy.copy(d) for d in rdgs1]
    for d in rdgswithts:
        d['received'] = currenttime
    consdict[ts11.date()] = rdgswithts
    
    with patch('process_temp_readings.send_alert') as mock_send_alert, \
         patch('process_temp_readings.time.time') as mock_time, \
         patch('process_temp_readings.write_readings') as mock_write_readings:
        mock_time.return_value = currenttime
        status = process_temp_readings.process_temperature_reading(xenv, events)
        assert mock_send_alert.call_count == 0
        assert status.temp_reading == rdgs1[2]['temperature']
        assert status.last_reading_ts == rdgs1[2]['timestamp']
        assert status.last_alert_ts == 42
        mock_write_readings.assert_called_with(xenv, 'eimer', consdict)

        # delay alert
        mock_send_alert.reset_mock()
        mock_time.reset_mock()
        mock_time.return_value = ts13.timestamp() + 4 * 3600
        mock_write_readings.reset_mock()
        xenv.s3.get_object.reset_mock()
        xenv.s3.get_object.side_effect = [dict(Body=io.StringIO(jsonrdgs), ContentLength=len(jsonrdgs))]
        status = process_temp_readings.process_temperature_reading(xenv, [event])
        mock_send_alert.assert_called_once_with(xenv, "Warning, received a delayed temperature reading. Delay is 4:00:00")
        assert status.temp_reading == rdgs1[2]['temperature']
        assert status.last_reading_ts == rdgs1[2]['timestamp']
        assert status.last_alert_ts == mock_time.return_value

        # low temperature alert
        mock_send_alert.reset_mock()
        mock_time.reset_mock()
        mock_time.return_value = currenttime
        mock_write_readings.reset_mock()
        xenv.s3.get_object.reset_mock()
        xenv.config.minimum_temperature = 10
        xenv.s3.get_object.side_effect = [dict(Body=io.StringIO(jsonrdgs), ContentLength=len(jsonrdgs))]
        status = process_temp_readings.process_temperature_reading(xenv, [event])
        mock_send_alert.assert_called_once_with(xenv, "The latest temperature reading of 3 (as of 2018.03.08 22:53:44) has fallen below the threshold of 10")
        assert status.temp_reading == rdgs1[2]['temperature']
        assert status.last_reading_ts == rdgs1[2]['timestamp']
        assert status.last_alert_ts == mock_time.return_value

        # empty readings1 alert
        mock_send_alert.reset_mock()
        mock_time.reset_mock()
        mock_write_readings.reset_mock()
        xenv.s3.get_object.reset_mock()
        xenv.s3.get_object.side_effect = [dict(Body=io.StringIO(jsonrdgs))]
        status = process_temp_readings.process_temperature_reading(xenv, [])
        mock_send_alert.assert_called_once_with(xenv, "Lambda event handler was invoked, but no temperature readings were processed.")
        assert status.temp_reading == 0
        assert status.last_reading_ts == 0
        assert status.last_alert_ts == mock_time.return_value

        # empty readings2 alert
        mock_send_alert.reset_mock()
        mock_time.reset_mock()
        mock_write_readings.reset_mock()
        xenv.s3.get_object.reset_mock()
        xenv.s3.get_object.side_effect = [dict(Body=io.StringIO(), ContentLength=0)]
        status = process_temp_readings.process_temperature_reading(xenv, [event])
        mock_send_alert.assert_called_once_with(xenv, "Lambda event handler was invoked, but no temperature readings were processed.")
        assert status.temp_reading == 0
        assert status.last_reading_ts == 0
        assert status.last_alert_ts == mock_time.return_value
        return

        # unknown source - no error/alert
        mock_send_alert.reset_mock()
        mock_time.reset_mock()
        mock_time.return_value = currenttime
        mock_write_readings.reset_mock()
        xenv.s3.get_object.reset_mock()
        otherevent = copy.copy(event)
        otherevent['eventSource'] = 'other'
        xenv.s3.get_object.side_effect = [dict(Body=io.StringIO(jsonrdgs), ContentLength=len(jsonrdgs))]
        status = process_temp_readings.process_temperature_reading(xenv, [event, othervent])
        assert mock_send_alert.call_count == 0
        assert status.temp_reading == rdgs1[2]['temperature']
        assert status.last_reading_ts == rdgs1[2]['timestamp']
        assert status.last_alert_ts == 42
        mock_write_readings.assert_called_with(xenv, 'eimer', consdict)

def test_process_scheduled_event():
    now = time.time()
    xenv = Mock()
    xenv.last_status = orig_status = process_temp_readings.Status(10, now - 3 * 60, 0)
    xenv.config = Mock()
    xenv.config.max_delay = 3
    with patch('process_temp_readings.send_alert') as mock_send_alert, \
         patch('process_temp_readings.time.time') as mock_time:
        mock_time.return_value = now
        event = dict(source='aws.events')
        res = process_temp_readings.process_scheduled_event(xenv, event)
        assert mock_send_alert.call_count == 0
        assert orig_status == res

        mock_send_alert.reset_mock()
        mock_time.return_value = now + 4 * 60 * 60
        res = process_temp_readings.process_scheduled_event(xenv, event)
        assert res.last_alert_ts == mock_time.return_value
        assert res.temp_reading == 10
        assert res.last_reading_ts == now - 3 * 60
        mock_send_alert.assert_called_once_with(xenv, "Failed to receive temperature readings for 4:03:00")

        mock_send_alert.reset_mock()
        xenv.last_status.last_reading_ts = 0
        xenv.last_status.last_alert_ts = None
        res = process_temp_readings.process_scheduled_event(xenv, event)
        assert mock_send_alert.call_count == 0
        assert res.last_alert_ts is None

def test_send_alert():
    now = time.time()
    xenv = Mock()
    xenv.last_status = process_temp_readings.Status(10, now - 3 * 60, 0)
    xenv.config = Mock()
    xenv.config.repeat_alert_hours = 3
    mock_snsClient = Mock()
    xenv.get_sns_client = lambda: mock_snsClient
    with patch('process_temp_readings.time.time') as mock_time:
        mock_time.return_value = now
        process_temp_readings.send_alert(xenv, 'duh!')
        assert mock_snsClient.publish.call_count == 1

        mock_snsClient.publish.reset_mock()
        xenv.last_status.last_alert_ts = now - 2 * 3600
        process_temp_readings.send_alert(xenv, 'duh!')
        assert mock_snsClient.publish.call_count == 0
        
    
def test_process_events():
    xenv = Mock()
    xenv.lambda_bucket = 'eimer'
    xenv.s3.get_object.return_value = t = dict(Body='config_body')
    with patch('process_temp_readings.read_config') as mock_read_config, \
         patch('process_temp_readings.Status.read_status') as mock_read_status, \
         patch('process_temp_readings.process_temperature_reading') as mock_process_reading, \
         patch('process_temp_readings.process_scheduled_event') as mock_scheduled_event, \
         patch('process_temp_readings.time.time') as mock_time, \
         patch('process_temp_readings.send_alert') as mock_send_alert:
        event1 = dict(Records = ['a', 'b', 'c'])
        mock_read_status.return_value = 42
        mock_process_reading.return_value = process_temp_readings.Status(1,2,3)
        mock_scheduled_event.return_value = process_temp_readings.Status(10,20,30)
        mock_time.return_value = 1000

        process_temp_readings.process_events(xenv, event1, None)
        xenv.s3.get_object.assert_called_once_with(Bucket='eimer', Key=process_temp_readings.LambdaStatus)
        assert xenv.last_status == 42
        mock_read_config.assert_called_once_with(xenv)
        mock_read_status.assert_called_once_with(t['Body'])
        mock_process_reading.assert_called_once_with(xenv, ['a', 'b', 'c'])
        assert mock_scheduled_event.call_count == 0
        assert mock_send_alert.call_count == 0
        xenv.s3.put_object.assert_called_once_with(Bucket = xenv.lambda_bucket,
                                                   Key = process_temp_readings.LambdaStatus,
                                                   Body = mock_process_reading.return_value.create_json().encode())
        
        event2 = dict(source='aws.events')
        for m in (xenv, xenv.s3.get_object, mock_read_config, mock_read_status, mock_process_reading, mock_scheduled_event, mock_send_alert, mock_time):
            m.reset_mock()
            
        process_temp_readings.process_events(xenv, event2, None)
        assert mock_process_reading.call_count == 0
        mock_scheduled_event.assert_called_once_with(xenv, event2)
        assert mock_send_alert.call_count == 0
        xenv.s3.put_object.assert_called_once_with(Bucket = xenv.lambda_bucket,
                                                   Key = process_temp_readings.LambdaStatus,
                                                   Body = mock_scheduled_event.return_value.create_json().encode())

        event3 = dict(type='dummy')
        for m in (xenv, xenv.s3.get_object, mock_read_config, mock_read_status, mock_process_reading, mock_scheduled_event, mock_send_alert, mock_time):
            m.reset_mock()

        last_status = process_temp_readings.Status(9, 99, 999)
        mock_read_status.return_value = last_status
        process_temp_readings.process_events(xenv, event3, None)
        assert mock_process_reading.call_count == 0
        assert mock_scheduled_event.call_count == 0
        mock_send_alert.assert_called_once_with(xenv, "Lambda function received an unexpected event.")        
        xenv.s3.put_object.assert_called_once_with(Bucket = xenv.lambda_bucket,
                                                   Key = process_temp_readings.LambdaStatus,
                                                   Body = process_temp_readings.Status(last_status.temp_reading,
                                                                                      last_status.last_reading_ts,
                                                                                      mock_time.return_value).create_json().encode())
        
