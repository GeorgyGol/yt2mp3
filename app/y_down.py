"""download mp3 from youtube
!!! need ffmpeg installed !!!
In linux (from personal expirience) func youtube_dl.download make strange MP3 format (not playing in some players)
so... in's converting by ffmpeg to mp3 - and in's work!

how to install ffmpeg (on linus):
   sudo apt update
   sudo apt install ffmpeg

check...
    ffmpeg -version
"""

from os import getpid
import youtube_dl
from app import redis_client, makkey, subkeys, REDIS_TTL, BASE_MP3_DIR
import re
import json
from collections import OrderedDict


class MyLogger(object):
    def debug(self, msg):
        # if re.search(r'\[download\]\s+\d+', msg):
        if msg[0] == '\r':
            # redis_client[self.keyproc] = msg[1:]
            self.rds.set(key=subkeys.progress, value=msg)
        else:
            return

    def info(self, msg):
        print('INF:', msg)

    def warning(self, msg):
        self.rds.set(key=subkeys.warning, value=f'WARNING: {msg}')

    def critical(self, msg):
        self.rds.set(key=subkeys.critical, value=f'CRITICAL ERROR: {msg}')

    def error(self, msg):
        self.rds.set(key=subkeys.error, value=msg)

    def __init__(self, proc_id=None, prefix=None):
        self.pid = proc_id
        self.prefix = prefix
        self.rds = RedisKeys(prefix=prefix, procID=proc_id)


# some service funtions

def get_formats(video_info):
    """
    get all possible formats for download - print its on console

    :param video_info: meta from Youtube
    :return:
    """

    print('=' * 50)
    # pprint(file_info)
    formats = video_info.get('formats', [video_info])
    for f in formats:
        print('FS:', f['filesize'], 'formID:', f['format_id'], 'formNote:', f['format_note'], 'EXT:', f['ext'])
    print('=' * 50)

def print_opt(opt, from_name=''):
    from pprint import pprint
    print(f'============ options from {from_name} =====================')
    pprint(opt)
    print('============================================================')

# ===============================================================

class RedisKeys():

    def __init__(self, procID=None, prefix=None):
        assert procID
        self._procID = str(procID)
        self._prefix = prefix

    def set(self, key:subkeys=subkeys.status, value=''):
        redis_client.setex(makkey(prefix=self._prefix, pid=self._procID, subkey=key), REDIS_TTL, value=value)

    def get(self, key:subkeys=subkeys.status):
        try:
            return redis_client[makkey(prefix=self._prefix, pid=self._procID, subkey=key)].decode()
        except KeyError:
            return None

    def _update_files_dict(self, _dict, filename, status, info):
        _dict.update({filename:{'status':status, 'info':info}})
        return _dict

    def set_file(self, filename='', status='done', info=''):
        try:
            jfs = self.get(key=subkeys.files)
            if jfs is None:
                jfs = json.dumps(self._update_files_dict(OrderedDict(), filename, status, info))
        except KeyError or TypeError:
            jfs = json.dumps(self._update_files_dict(OrderedDict(), filename, status, info))
            # self.set(key=subkeys.files, value=jfs)
            # return

        jf = OrderedDict(json.loads(jfs))
        try:
            jf[filename]['status'] = status
            jf[filename]['info'] = info
        except KeyError:
            jf = self._update_files_dict(jf, filename, status, info)
            # jf.update({filename:{'status':status, 'info':info}})
        self.set(key=subkeys.files, value=json.dumps(jf))

    def get_file(self):
        # try:
        val = self.get(key=subkeys.files)
        if val is not None:
            return OrderedDict(json.loads(val))
        else:
            return OrderedDict()
        # except:
        #     return OrderedDict()

    def clear_keys(self):
        redis_client.setex(makkey(prefix=self._prefix,
                                  pid=self._procID, subkey=subkeys.warning), REDIS_TTL, value='')
        redis_client.setex(makkey(prefix=self._prefix,
                                  pid=self._procID, subkey=subkeys.error), REDIS_TTL, value='')

class dwnOptions():

    def _audio_opt(self, format, logger, name_template):
        return {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format,
                }],
                'outtmpl': name_template,
                'logger': logger,
                'prefer_ffmpeg': True,
                'keepvideo': False
            }

    def _video_opt(self, format, logger, name_template, vq):
        # post_proc = [{
        #     'key': 'FFmpegVideoConvertor',
        #     'preferedformat': audio_format,
        #     'merge-output-format': audio_format,
        #     'preferredcodec': audio_format,
        # }]
        post_proc = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': format,
            'merge-output-format': format,
            'preferredcodec': format,
        }]

        # ffmpform = 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]'
        if vq == 'best':
            ffmpform = 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]'
        elif vq == 'tiny':
            ffmpform = 'worstvideo[ext=mp4]+bestaudio/worstbest[ext=mp4]'
        else:
            try:
                ht = int(vq)
                ffmpform = f'bestvideo[height <= {ht}][ext=mp4]+bestaudio/best[height <= {ht}][ext=mp4]'
            except:
                ffmpform = 'worstvideo[ext=mp4]+bestaudio/worst[ext=mp4]'
        # ffmpform = 'bestvideo[height <= 480][ext=mp4]+bestaudio/best[height <= 480][ext=mp4]'

        return {
            'format': ffmpform,
            'outtmpl': name_template,
            'logger': logger,
            'prefer_ffmpeg': True,
            'keepvideo': True
        }

    def __init__(self, which='audio', format='mp3', logger=None, name_template='', video_quality='480'):
        if which=='audio':
            self.options = self._audio_opt(format, logger, name_template)
        elif which=='video':
            self.options = self._video_opt(format, logger, name_template, video_quality)

        # pprint(options)

def _prepare_download(url=None, logger=None, base_path=None):

    def get_info(json_str):
        return {'id': json_str['id'], 'title': json_str['title'],
                'url': json_str['webpage_url']}

    opt = {'logger': logger}

    with youtube_dl.YoutubeDL(opt) as ydl:
        info = ydl.extract_info(url=url, download=False)

        # get_formats(info)
        src = list()
        try:
            if info['_type'] == 'playlist':
                src = [get_info(e) for e in info['entries']]
                template_name = f'{base_path}%(playlist)s/%(title)s.%(ext)s'
        except:
            template_name = f'{base_path}%(title)s.%(ext)s'
            src = [get_info(info), ]

        # print_opt(info)
        return src, template_name



def download1(strUrl=None, keep_video=False, audio_format='mp3',
              pre=None, base_path = BASE_MP3_DIR, video_quality='480', start_from=0, stop_at=1000):
    assert strUrl

    logg = MyLogger(prefix=pre, proc_id=getpid())
    rds = RedisKeys(prefix=pre, procID=getpid())
    rds.set(key=subkeys.status, value='STARTED')
    try:
        source, templ_file = _prepare_download(logger=logg, url=strUrl, base_path=base_path)
    except youtube_dl.utils.DownloadError as e:
        rds.set(key=subkeys.status, value='STOPED')
        # rds.set(key=subkeys.error, value=e)
        return -1

    opts = dwnOptions(which='video' if keep_video else 'audio', video_quality=video_quality,
                      format=audio_format, logger=logg, name_template=templ_file)

    with youtube_dl.YoutubeDL(opts.options) as ydl:
        #         ydl.cache.remove()
        # ydl.add_progress_hook(lambda x: print('.', end=' '))

        for num, s in enumerate(source):
            rds.clear_keys()

            file_info = ydl.extract_info(s['url'], download=False)
            filename = ydl.prepare_filename(file_info)

            i = filename.rfind('.')
            filename = f'{filename[:i]}.{audio_format}'
            filename = re.sub(BASE_MP3_DIR, '', filename)[1:]

            if start_from <= num <= stop_at:
                rds.set_file(filename=filename, status='process')

                # TODO: error 'forbidden'
                try:
                    ydl.download([s['url']])
                    rds.set_file(filename=filename, status='done')
                except youtube_dl.utils.DownloadError as yterr:
                    rds.set_file(filename=filename, status='error', info='download error')
                except:
                    rds.set_file(filename=filename, status='error', info='some base error')
            else:
                rds.set_file(filename=filename, status='omited', info='by user')


    rds.set(key=subkeys.status, value='STOPED')
    return 0



if __name__ == '__main__':

    # video_url = 'https://www.youtube.com/watch?v=mb-Cnwi9BqA'
    # video_url = 'https://www.youtube.com/playlist?list=PLkz3fL8MYDt5FbiY3A1g65CdGaI_CISm4'
    #
    # download1(strUrl=video_url)


    print('All done.')