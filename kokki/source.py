
from __future__ import with_statement

__all__ = ["Source", "Template", "StaticFile", "DownloadSource"]

import os
from kokki import environment
from kokki.exceptions import Fail

class Source(object):
    def get_content(self):
        raise NotImplementedError()

    def get_checksum(self):
        return None

    def __call__(self):
        return self.get_content()

class StaticFile(Source):
    def __init__(self, name, env=None):
        self.name = name
        self.env = env or environment.Environment.get_instance()

    def get_content(self):
        try:
            cookbook, name = self.name.split('/', 1)
        except ValueError:
            raise Fail("[StaticFile(%s)] Path must include cookbook name (e.g. 'nginx/nginx.conf')" % self.name)
        cb = self.env.cookbooks[cookbook]
        path = os.path.join(cb.path, "files", name)
        with open(path, "rb") as fp:
            return fp.read()

try:
    from jinja2 import Environment, BaseLoader, TemplateNotFound
except ImportError:
    class Template(Source):
        def __init__(self, name, variables=None, env=None):
            raise Exception("Jinja2 required for Template")
else:
    class TemplateLoader(BaseLoader):
        def __init__(self, env=None):
            self.env = env or environment.Environment.get_instance()

        def get_source(self, environment, template):
            try:
                cookbook, name = template.split('/', 1)
            except ValueError:
                raise Fail("[Template(%s)] Path must include cookbook name (e.g. 'nginx/nginx.conf.j2')" % template)
            cb = self.env.cookbooks[cookbook]
            path = os.path.join(cb.path, "templates", name)
            if not os.path.exists(path):
                raise TemplateNotFound("%s at %s" % (template, path))
            mtime = os.path.getmtime(path)
            with open(path, "rb") as fp:
                source = fp.read().decode('utf-8')
            return source, path, lambda:mtime == os.path.getmtime(path)

    class Template(Source):
        def __init__(self, name, variables=None, env=None):
            self.name = name
            self.env = env or environment.Environment.get_instance()
            self.context = variables.copy() if variables else {}
            self.template_env = Environment(loader=TemplateLoader(self.env), autoescape=False)
            self.template = self.template_env.get_template(self.name)

        def get_content(self):
            self.context.update(
                env = self.env,
                repr = repr,
                str = str,
                bool = bool,
            )
            rendered = self.template.render(self.context)
            return rendered + "\n" if not rendered.endswith('\n') else rendered

import urllib2,urlparse,hashlib
class DownloadSource(Source):
    def __init__(self, url, cache=True, md5sum=None, env=None):
        self.env = env or environment.Environment.get_instance()
        self.url = url
        self.md5sum = md5sum
        self.cache = cache
        if not 'download_path' in env.config:
            env.config.download_path = '/var/tmp/downloads'
        if not os.path.exists(env.config.download_path):
            os.makedirs(self.env.config.download_path)

    def get_content(self):
        file = os.path.basename(urlparse.urlparse(self.url).path)
        content = None
        if not self.cache or not os.path.exists(os.path.join(self.env.config.download_path, file)):
            web_file = urllib2.urlopen(self.url)
            content = web_file.read()
        else:
            update = False
            fp = open(os.path.join(self.env.config.download_path, file))
            try:
                content = fp.read()
            finally:
                fp.close()
            if self.md5sum:
                m = hashlib.md5()
                m.update(content)
                md5 = m.hexdigest()
                if md5 != self.md5sum:
                    web_file = urllib2.urlopen(self.url)
                    content = web_file.read()
                    update = True
            if self.cache and update:
                fp = open(os.path.join(self.env.config.download_path, file), 'w')
                try:
                    fp.write(content)
                finally:
                    fp.close()
        return content
