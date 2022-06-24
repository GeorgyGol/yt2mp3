import os
import shutil
from multiprocessing import Process, active_children
import re
from flask import render_template, request, session, url_for, send_from_directory, redirect

from app import app, __version__, redis_client, makkey, subkeys, REDIS_TTL, BASE_MP3_DIR, MP3_DIR
from app.down_form import DWNForm
from app.y_down import download1, RedisKeys

def down_load(url, sid, keep_video, form, video_quality, start_from, stop_at):
    rds = RedisKeys(procID=os.getpid(), prefix=sid)
    try:
        download1(strUrl=url, pre=sid, audio_format=form, video_quality=video_quality,
                  base_path=f'{BASE_MP3_DIR}/{os.getpid()}/', keep_video=keep_video,
                  start_from=int(start_from), stop_at=int(stop_at))
    finally:
        rds.set(subkeys.status, value='STOPED')


@app.route('/', methods =['GET', 'POST'], defaults={'videq':'480'})
@app.route('/<videq>', methods =['GET', 'POST'])
def index(videq):
    dwn_form = DWNForm()

    if request.method == 'POST':
        if dwn_form.validate_on_submit():
            url = dwn_form.yt_url.data
            file_format= f'mp{4 if  dwn_form.save_video.data else 3}'
            start_from = dwn_form.start_from.data
            stop_at = dwn_form.stop_at.data
            # print(f'{start_from=}')

            p = Process(target=down_load, args=(url, session.sid, dwn_form.save_video.data, file_format,
                                                videq, start_from, stop_at))
            if 'save' in request.form:
                dwn_form.stop.render_kw['disabled']=False
                dwn_form.submit.render_kw['disabled'] = True
                p.daemon = True
                p.start()
                try:
                    if session['cur_proc'] != -1:
                        shutil.rmtree(os.path.join(BASE_MP3_DIR, session['cur_proc']), ignore_errors=True)
                except KeyError:
                    session['cur_proc'] = -1
                    # first start
                session['cur_proc'] = str(p.pid)

            else:
                dwn_form.stop.render_kw['disabled'] = True
                dwn_form.submit.render_kw['disabled'] = False
                dwn_form.start_from.data=0
                dwn_form.stop_at.data = 1000

                for chp in active_children():
                    if str(chp.pid) == session['cur_proc']:
                        chp.terminate()

                shutil.rmtree(os.path.join(BASE_MP3_DIR, session['cur_proc']), ignore_errors=True)
                session['cur_proc'] = -1


    return render_template('main.html', version = __version__, d_form=dwn_form, videoq=videq)

@app.route('/data')
def data():
    def color_mess(message, alert_type='alert-info'):
        return f'''<div class ="alert {alert_type}" role="alert">{message}</div>'''

    try:
        if session['cur_proc'] != -1:
            rds = RedisKeys(prefix=session.sid, procID=session['cur_proc'])
            stat =  rds.get(key=subkeys.status)
            progs = rds.get(key=subkeys.progress)
            dwerr = rds.get(key=subkeys.error)
            warning = rds.get(key=subkeys.warning)
            jfiles =  rds.get_file()

            if stat == 'STARTED':
                _stat_mess = color_mess(f'''Рабочий процесс № {session['cur_proc']} - {stat}<br>''')
            else:
                _stat_mess = color_mess(f'''Рабочий процесс № {session['cur_proc']} - {stat}<br>''',
                                        alert_type='alert-success')
            strMess = _stat_mess

            if warning:
                strMess += color_mess(warning, alert_type='alert-warning')

            for k, v in jfiles.items():
                if v['status'] == 'done':
                    strMess += f'<a href="{os.path.join(MP3_DIR, k)}" target="blank">{k}</a><br>'
                elif v['status'] == 'process':
                    strMess += f'{k} --> {progs}'
                else:
                    strMess += f'{k}: {v["status"]} --> {v["info"]}<br>'
            if dwerr:
                _errm = color_mess(dwerr, alert_type='alert-danger')

                strMess += _errm
        else:
            strMess = 'Ждем-с команд-с...'
    except KeyError:
    #     # first start - not rpoc
        strMess = 'Начнем?...'
    return strMess

@app.route(f'/{MP3_DIR}/<path:filename>', methods=['GET', 'POST'])
def download(filename):

    if os.path.exists(os.path.join(BASE_MP3_DIR, filename)):
        return send_from_directory(MP3_DIR, filename, as_attachment=True)
    else:
        parts = os.path.splitext(filename)
        filename = f'{parts[0]}.mkv'
        return send_from_directory(MP3_DIR, filename, as_attachment=True)
    # try:
    #     # return send_file(fp, as_attachment=True)
    #     return send_from_directory('static/mp3', filename, as_attachment=True)
    # except:
    #     parts = os.path.splitext(fp)
    #     fp = f'{parts[0]}.mkv'
    #     return send_from_directory('static/mp3', filename, as_attachment=True)
        # return send_file(fp, as_attachment=True)


# @app.route('/<videoq>')
# def setupvideo(videoq):
#     print(videoq)

@app.route('/clear', methods=['GET', 'POST'])
def stoped():
    for chp in active_children():
        if str(chp.pid) == session['cur_proc']:
            chp.terminate()
    session['cur_proc'] = -1
    shutil.rmtree(BASE_MP3_DIR, ignore_errors=True)
    return  redirect(url_for('index'))

if __name__ == '__main__':

    app.run(port=5052)
