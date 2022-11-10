from .setup import *


class ModuleVod(PluginModuleBase):

    def __init__(self, P):
        super(ModuleVod, self).__init__(P, name='vod', first_menu='list')
        self.db_default = {
            f'{self.name}_db_version' : '2',
            'vod_remote_path' : '',
            'vod_download_mode' : 'none', #Nothing, 모두받기, 블랙, 화이트
            'vod_blacklist_genre' : '',
            'vod_blacklist_program' : '',
            'vod_whitelist_genre' : '',
            'vod_whitelist_program' : '',
            'vod_item_last_list_option': '',
            f'{self.name}_db_delete_day': '30',
            f'{self.name}_db_auto_delete': 'False',
            'vod_use_notify': 'False',
        }
        self.web_list_model = ModelVodItem


    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'option':
            mode = arg1
            value = arg2
            value_list = P.ModelSetting.get_list(f'vod_{mode}', '|')
            if value in value_list:
                ret['ret'] = 'warning'
                ret['msg'] = '이미 설정되어 있습니다.'
            else:
                if len(value_list) == 0:
                    P.ModelSetting.set(f'vod_{mode}', value)
                else:
                    P.ModelSetting.set(f'vod_{mode}', P.ModelSetting.get(f'vod_{mode}') + ' | ' + value)
                ret['msg'] = '추가하였습니다'
        elif command == 'request_copy':
            item = ModelVodItem.get_by_id(arg1)
            ret = self.share_copy(item)
            if item is not None:
                item.save()
            return jsonify(ret)
        elif command == 'db_delete':
            if self.web_list_model.delete_by_id(arg1):
                ret['msg'] = '삭제하였습니다.'
            else:
                ret['ret'] = 'warning'
                ret['msg'] = '삭제 실패'

        return jsonify(ret)


    def process_discord_data(self, data):
        item = ModelVodItem.process_discord_data(data)
        if item is None:
            return
        try:
            flag_download = self.condition_check_download_mode(item)
            if flag_download:
                self.share_copy(item)
            if P.ModelSetting.get_bool('vod_use_notify'):
                from tool import ToolNotify
                msg = f'봇 VOD 수신\n파일: {item.filename}\n로그: {item.log}'
                ToolNotify.send_message(msg, image_url=item.meta_poster, message_id=f"{P.package_name}_{self.name}")
        except Exception as e:
            P.logger.error('Exception:%s', e)
            P.logger.error(traceback.format_exc())
        finally:
            item.save()



    def share_copy(self, item):
        try:
            vod_remote_path = P.ModelSetting.get('vod_remote_path')
            if vod_remote_path == '':
                return {'ret':'warning', 'msg':'리모트 경로 정보가 없습니다.'}
            try:
                import gds_tool
                PP = F.PluginManager.get_plugin_instance('gds_tool')
                if PP == None:
                    raise Exception()
            except:
                return {'ret':'warning', 'msg':'구글 드라이브 공유 플러그인이 설치되어 있지 않습니다.'}

            ret = PP.add_copy(item.fileid, item.filename, 'bot_vod', item.meta_genre, item.size, 1, copy_type='file', remote_path=vod_remote_path)

            item.share_request_time = datetime.now()
            item.request_db_id = ret['request_db_id'] if 'request_db_id' in ret else None
            item.save()
            if ret['ret'] == 'success':
                return {'ret':'success', 'msg': '요청하였습니다.'}
            elif ret['ret'] == 'remote_path_is_none':
                return {'ret':'warning', 'msg': '리모트 경로가 없습니다.'}
            elif ret['ret'] == 'already':
                return {'ret':'warning', 'msg': '이미 요청 DB에 있습니다.<br>상태: ' + ret['status']}
            elif ret['ret'] == 'cannot_access':
                return {'ret':'warning', 'msg': '권한이 없습니다.'}
            else:
                return {'ret':'warning', 'msg': '실패'}
        except Exception as e:
            P.logger.error('Exception:%s', e)
            P.logger.error(traceback.format_exc())


    def condition_check_download_mode(self, item):
        try:
            vod_download_mode = P.ModelSetting.get('vod_download_mode')
            if vod_download_mode == 'none':
                return False
            if vod_download_mode == 'blacklist':
                flag_download = True
                if item.meta_title is None:
                    item.log += u'메타 정보 없음. 다운:On'
                    return flag_download
                vod_blacklist_genre = P.ModelSetting.get_list('vod_blacklist_genre', '|')
                vod_blacklist_program = P.ModelSetting.get_list('vod_blacklist_program', '|')
                if len(vod_blacklist_genre) > 0 and item.meta_genre in vod_blacklist_genre:
                    flag_download = False
                    item.log += '제외 장르. 다운:Off'
                if flag_download:
                    for program_name in vod_blacklist_program:
                        if item.meta_title.replace(' ', '').find(program_name.replace(' ', '')) != -1:
                            flag_download = False
                            item.log += '제외 프로그램. 다운:Off'
                            break
                if flag_download:
                    item.log += '블랙리스트 모드. 다운:On'
            else:
                flag_download = False
                if item.meta_title is None:
                    item.log += 'Daum 정보 없음. 다운:Off'
                    return flag_download
                vod_whitelist_genre = P.ModelSetting.get_list('vod_whitelist_genre', '|')
                vod_whitelist_program = P.ModelSetting.get_list('vod_whitelist_program', '|')

                if len(vod_whitelist_genre) > 0 and item.daum_genre in vod_whitelist_genre:
                    flag_download = True
                    item.log += '포함 장르. 다운:On'
                if flag_download == False:
                    for program_name in vod_whitelist_program:
                        if item.meta_title.replace(' ', '').find(program_name.replace(' ', '')) != -1:
                            flag_download = True
                            item.log += '포함 프로그램. 다운:On'
                            break
                if not flag_download:
                    item.log += '화이트리스트 모드. 다운:Off'
        except Exception as e: 
            P.logger.error('Exception:%s', e)
            P.logger.error(traceback.format_exc())
        return flag_download




class ModelVodItem(ModelBase):
    P = P
    __tablename__ = 'vod_item'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)
    share_request_time = db.Column(db.DateTime)
    request_db_id = db.Column(db.Integer)
    share_completed_time = db.Column(db.DateTime)
    data = db.Column(db.JSON)
    fileid = db.Column(db.String)
    filename = db.Column(db.String)
    size = db.Column(db.Integer)
    filename_name = db.Column(db.String)
    filename_no = db.Column(db.Integer)
    filename_release = db.Column(db.String)
    filename_date = db.Column(db.String)
    filename_quality = db.Column(db.String)
    meta_genre = db.Column(db.String)
    meta_code = db.Column(db.String)
    meta_title = db.Column(db.String)
    meta_poster = db.Column(db.String)
    log = db.Column(db.String)

    def __init__(self):
        self.created_time = datetime.now()
        self.log = ''


    @classmethod
    def process_discord_data(cls, data):
        try:
            #logger.error(d(data))
            entity = cls.get_by_filename(data['msg']['data']['f'])
            if entity is not None:
                return
            entity =  ModelVodItem()
            entity.data = data
            entity.fileid = data['msg']['data']['id']
            entity.filename = data['msg']['data']['f']
            entity.size = data['msg']['data']['s']

            entity.filename_name = data['msg']['data']['vod']['name']
            entity.filename_no = data['msg']['data']['vod']['no']
            entity.filename_release = data['msg']['data']['vod']['release']
            entity.filename_date =  data['msg']['data']['vod']['date']
            entity.filename_quality = data['msg']['data']['vod']['quality']

            if data['msg']['data']['meta'] is not None:
                entity.meta_genre = data['msg']['data']['meta']['genre']
                entity.meta_code = data['msg']['data']['meta']['code']
                entity.meta_title = data['msg']['data']['meta']['title']
                entity.meta_poster = data['msg']['data']['meta']['poster']
            else:
                entity.meta_genre = u'미분류'
            entity.save()
            return entity
        except Exception as e:
            P.logger.error('Exception:%s', e)
            P.logger.error(traceback.format_exc())   


    @classmethod
    def get_by_filename(cls, filename):
        try:
            with F.app.app_context():
                return F.db.session.query(cls).filter_by(filename=filename).first()
        except Exception as e:
            cls.P.logger.error(f'Exception:{str(e)}')
            cls.P.logger.error(traceback.format_exc())


    
    @classmethod
    def make_query(cls, req, order='desc', search='', option1='all', option2='all'):
        with F.app.app_context():
            query = cls.make_query_search(F.db.session.query(cls), search, cls.filename)
            if option1 == 'request_true':
                query = query.filter(cls.share_request_time != None)
            elif option1 == 'request_false':
                query = query.filter(cls.share_request_time == None)
            
            if order == 'desc':
                query = query.order_by(desc(cls.id))
            else:
                query = query.order_by(cls.id)
            return query


    @classmethod
    def web_list(cls, req):
        ret = super().web_list(req)
        try:
            ModelRequestItem = F.PluginManager.get_plugin_instance('gds_tool').ModelRequestItem
            for item in ret['list']:
                if item['request_db_id'] != None:
                    req_item = ModelRequestItem.get_by_id(item['request_db_id'])
                    if req_item != None:
                        item['request_item'] = req_item.as_dict()
                    else:
                        item['request_item'] = None
        except Exception as e:
            cls.P.logger.error(f'Exception:{str(e)}')
            cls.P.logger.error(traceback.format_exc())
        return ret