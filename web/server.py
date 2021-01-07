import os
import os.path
import sys
sys.path.append(os.getcwd() + '/../src')

import cherrypy
from cherrypy.lib import static
from convert import convert

import random
import string
import shutil

current_dir = os.path.dirname(os.path.abspath(__file__))

config = {
  'global' : {
    'server.max_request_body_size' : 20000000
  },
  '/static': {
    'tools.staticdir.on': True,
     'tools.staticdir.dir': os.path.join(current_dir, 'static')
    }
}

def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str
   
class FileConvert(object):
    @cherrypy.tools.register('on_end_request')
    def cleanup():
        print('cleanup: ' + cherrypy.request.filename)
        if cherrypy.request.filename:
            shutil.rmtree(cherrypy.request.filename)
            cherrypy.request.filename = None

    @cherrypy.expose
    def index(self):
        return """
        <html><body>
            <h2>Convert Rocksmith .psarc file between pc and mac</h2>
            <form action="upload" method="post" enctype="multipart/form-data">
            <input type="file" name="ufile" /><br /><br />
            <input type="submit" value="convert"/>
            </form>
        </body></html>
        """

    @cherrypy.expose
    @cherrypy.tools.cleanup()
    def upload(self, ufile):
        random = get_random_string(8)
        upload_path = os.path.normpath('/tmp/' + random)
        os.mkdir(upload_path)
        upload_file = os.path.join(upload_path, ufile.filename)
        with open(upload_file, 'wb') as out:
            while True:
                data = ufile.file.read(8192)
                if not data:
                    break
                out.write(data)
        filename = convert(upload_file, upload_path)
        cherrypy.request.filename = upload_path
        return static.serve_file(filename, 'application/x-download',
                                    'attachment')

if __name__ == '__main__':
    cherrypy.quickstart(FileConvert(), '/', config)
