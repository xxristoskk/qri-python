import base64
import io
import json
import pandas

from .cmd_util import shell_exec, QriClientError
from subprocess import Popen, PIPE


_inst = None


def instance():
    global _inst
    if _inst is None:
        print
        proc = Popen(['which', 'qri'], stdout=PIPE)
        stdout, err = proc.communicate()
        if proc.returncode == 0:
            # Have a local qri binary
            _inst = LocalQriBinaryRepo()
        else:
            # Send http requests to api.qri.cloud
            _inst = CloudAPIRepo()
    return _inst


def set_instance(obj):
    global _inst
    _inst = obj


class LocalQriBinaryRepo(object):
    def get_dataset_object(self, ref):
        cmd = 'qri get --format json %s' % ref.human()
        result, err = shell_exec(cmd)
        if err:
            raise QriClientError(err)
        return json.loads(result)

    def list_dataset_objects(self, username=None):
        if username is not None:
            raise QriClientError('listing with username not supported')
        cmd = 'qri list --format json'
        result, err = shell_exec(cmd)
        if err:
            raise QriClientError(err)
        return json.loads(result)

    def pull_dataset(self):
        cmd = 'qri pull %s' % ref.human()
        result, err = shell_exec(cmd)
        if err:
            raise QriClientError(err)
        return result

    def load_body(self, ref, structure):
        if structure.format != 'csv':
            raise RuntimeError('Format "%s" not supported' % structure.format)
        cmd = 'qri get body %s' % ref.human()
        result, err = shell_exec(cmd)
        if err:
            raise QriClientError(err)
        stream = io.StringIO(str(result, 'utf8'))
        columns = [e for e in structure.schema['items']['items']]
        col_names = [c['title'] for c in columns]
        types = {c['title']: pd_type(c['type']) for c in columns}
        header = 0 if structure.format_config.get('headerRow') else None
        df = None
        try:
            # Try to parse the csv using the schema
            df = pandas.read_csv(stream, header=header, names=col_names,
                                 dtype=types)
        except (TypeError, ValueError):
            # If pandas encountered parse errors, reparse without datatypes
            stream = io.StringIO(str(result, 'utf8'))
            df = pandas.read_csv(stream, header=header, names=col_names)
        return df


class CloudAPIRepo(object):
    def get_dataset_object(self, ref):
        r = requests.get('https://api.qri.cloud/get/%s' % ref.human())
        return json.loads(r.text)['data']['dataset']

    def list_dataset_objects(self, username=None):
        raise NotImplementedError('CloudAPIRepo.list_dataset_objects')

    def load_body(self, ref, structure):
        raise NotImplementedError('CloudAPIRepo.load_body_dataframe')


def from_json(json_text):
    return pandas.read_json(json_text)


def base64_decode(bdata):
    return base64.b64decode(bdata)


def pd_type(t):
    if t == 'integer':
        return 'int64'
    elif t == 'number':
        return 'float64'
    elif t == 'string':
        return 'string'
    elif t == 'bool':
        return 'bool'
    raise RuntimeError('Unknown type: "%s"' % t)
