from .setup import *


class ModuleShareMovie(PluginModuleBase):

    def __init__(self, P):
        super(ModuleShareMovie, self).__init__(P, name='share_movie', first_menu='list')
        self.db_default = {
            f'{self.name}_db_version' : '1',
            f'{self.name}_db_delete_day': '30',
            f'{self.name}_db_auto_delete': 'False',

            f'{self.name}_remote_path' : '',
            f'{self.name}_item_last_list_option': '',
            f'{self.name}_use_notify': 'False',

            f'{self.name}_download_mode' : 'none', #Nothing, 블랙, 화이트
            f'{self.name}_blacklist_cate' : '',
            f'{self.name}_blacklist_genre' : '',
            f'{self.name}_blacklist_country' : '',
            f'{self.name}_blacklist_year' : '',
            f'{self.name}_whitelist_cate' : '',
            f'{self.name}_whitelist_genre' : '',
            f'{self.name}_whitelist_country' : '',
            f'{self.name}_whitelist_year' : '',
        }
        self.web_list_model = ModelShareMovieItem


    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'request_copy':
            item = ModelShareMovieItem.get_by_id(arg1)
            ret = self.share_copy(item)
            if item is not None:
                item.save()
            return jsonify(ret)
        return jsonify(ret)


    def process_discord_data(self, data):
        item = ModelShareMovieItem.process_discord_data(data)
        if item is None:
            return
        try:
            flag_download = self.condition_check_download_mode(item)
            item.log += '다운: ON' if flag_download else '다운: OFF'
            item.save()
            if flag_download:
                self.share_copy(item)
            if P.ModelSetting.get_bool('share_movie_use_notify'):
                from tool import ToolNotify
                msg = f'봇 S-MOVIE 수신\n{item.foldername}\n로그: {item.log}'
                ToolNotify.send_message(msg, image_url=item.poster, message_id=f"{P.package_name}_{self.name}")
        except Exception as e:
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())
        finally:
            item.save()



    def share_copy(self, item):
        try:
            remote_path = P.ModelSetting.get(f'{self.name}_remote_path')
            if remote_path == '':
                return {'ret':'warning', 'msg':'리모트 경로 정보가 없습니다.'}
            try:
                import gds_tool
                PP = F.PluginManager.get_plugin_instance('gds_tool')
                if PP == None:
                    raise Exception()
            except:
                return {'ret':'warning', 'msg':'구글 드라이브 공유 플러그인이 설치되어 있지 않습니다.'}

            ret = PP.add_copy(item.folderid, item.foldername, f'bot_{self.name}', item.category, item.size, item.count, copy_type='folder', remote_path=remote_path)

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
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())


    def condition_check_download_mode(self, item):
        try:
            download_mode = P.ModelSetting.get(f'{self.name}_download_mode')
            if download_mode == 'none':
                return False
            if download_mode == 'blacklist':
                item.log += "블랙리스트: "
                flag_download = True
                cond_cate = P.ModelSetting.get_list(f'{self.name}_blacklist_cate', ',')
                if len(cond_cate) > 0 and item.category in cond_cate:
                    return False
                cond_genre = P.ModelSetting.get_list(f'{self.name}_blacklist_genre', ',')
                if len(cond_genre) > 0:
                    for genre in item.genre:
                        if genre in cond_genre:
                            return False

                cond_country = P.ModelSetting.get_list(f'{self.name}_blacklist_country', ',')
                if len(cond_country) > 0:
                    for country in item.country:
                        if country in cond_country:
                            return False

                cond_year = P.ModelSetting.get(f'{self.name}_blacklist_year')
                if cond_year != '' and '-' in cond_year:
                    tmp = cond_year.split('-')
                    if int(tmp[0]) <= item.year and item.year >= int(tmp[1]):
                        return False
                return True

            elif download_mode == 'whitelist':
                item.log += "화이트리스트: "
                flag_download = False
                cond_cate = P.ModelSetting.get_list(f'{self.name}_whitelist_cate', ',')
                if len(cond_cate) > 0 and item.category in cond_cate:
                    return True
                cond_genre = P.ModelSetting.get_list(f'{self.name}_whitelist_genre', ',')
                if len(cond_genre) > 0:
                    for genre in item.genre:
                        if genre in cond_genre:
                            return True

                cond_country = P.ModelSetting.get_list(f'{self.name}_whitelist_country', ',')
                if len(cond_country) > 0:
                    for country in item.country:
                        if country in cond_country:
                            return True

                cond_year = P.ModelSetting.get(f'{self.name}_whitelist_year')
                if cond_year != '' and '-' in cond_year:
                    tmp = cond_year.split('-')
                    if int(tmp[0]) <= item.year and item.year >= int(tmp[1]):
                        return True
                return flag_download

        except Exception as e: 
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())
        return flag_download




class ModelShareMovieItem(ModelBase):
    P = P
    __tablename__ = 'share_movie_item'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)
    data = db.Column(db.JSON)
    share_request_time = db.Column(db.DateTime)
    request_db_id = db.Column(db.Integer)
    log = db.Column(db.String)

    category = db.Column(db.String)
    subject = db.Column(db.String)
    folderid = db.Column(db.String)
    size = db.Column(db.Integer)
    count = db.Column(db.Integer)
    foldername = db.Column(db.String)

    title = db.Column(db.String)
    originaltitle = db.Column(db.String)
    genre = db.Column(db.String)
    code = db.Column(db.String)
    year = db.Column(db.Integer)
    poster = db.Column(db.String)
    country = db.Column(db.String)
    

    def __init__(self):
        self.created_time = datetime.now()
        self.log = ''


    @classmethod
    def process_discord_data(cls, data):
        try:
            P.logger.error(d(data))
            entity = cls.get_by_folderid(data['msg']['data']['folderid'])
            if entity is not None:
                return
            entity =  ModelShareMovieItem()
            entity.data = data

            entity.category = data['msg']['data']['ca']
            entity.subject = data['msg']['data']['subject']
            entity.folderid = data['msg']['data']['folderid']
            entity.size = data['msg']['data']['size']
            entity.count = data['msg']['data']['count']
            entity.foldername = data['msg']['data']['foldername']

            entity.title = data['msg']['data']['meta']['title']
            entity.originaltitle = data['msg']['data']['meta']['originaltitle']
            entity.genre = ','.join(data['msg']['data']['meta']['genre'])
            entity.code = data['msg']['data']['meta']['code']
            entity.year = data['msg']['data']['meta']['year']
            entity.poster = data['msg']['data']['meta']['poster']
            entity.country = ','.join(data['msg']['data']['meta']['country'])
            entity.save()
            return entity
        except Exception as e:
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())   


    @classmethod
    def get_by_folderid(cls, folderid):
        try:
            with F.app.app_context():
                return F.db.session.query(cls).filter_by(folderid=folderid).first()
        except Exception as e:
            cls.P.logger.error(f'Exception:{str(e)}')
            cls.P.logger.error(traceback.format_exc())


    
    @classmethod
    def make_query(cls, req, order='desc', search='', option1='all', option2='all'):
        with F.app.app_context():
            query = cls.make_query_search(F.db.session.query(cls), search, cls.foldername)
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