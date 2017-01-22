import json
import flask
from pymongo import MongoClient

import server.my_ast  as AST
import server.my_np_func as np_func

app = flask.Flask(__name__)

all_func_dict = dict()
for func_name in np_func.get_all_func_name():
    x = func_name.replace('_', '.').replace('..', '_')
    all_func_dict[x] = getattr(np_func, func_name)

def get_mongo_conn(env):            #TODO: Not tested
    config = json.loads(''.join(line.rstrip() for line in open(env)))
    if 'dbloc' not in config or 'dbname' not in config:
        raise ValueError('Config insufficient. dbloc and dbname required.')
    client = MongoClient('mongodb://{0}'.format(config['dbloc']))

    db = client[config['dbname']]

    return db['record']


def insert_record(conn, record):    #TODO: Not tested
    r = []
    for node in record:
        if isinstance(node, AST.Token) and node.identifier.startswith('Call:'):
            r.append(dict({
                'identifier': node.identifier.split(':')[1],
                'dim': node.dim
            }))
    try:
        conn.insert_one({'nodes': r})
    except Exception as e:
        pass


def get_predefined(p):
    ret = dict()
    if not isinstance(p, list):
        return ret
    for item in p:
        if 'name' not in item or 'type' not in item:
            continue
        if item['type'] == 'array' and 'dim' in item and isinstance(item['dim'], list):
            ret[item['name']] = AST.Token(tuple(item['dim']))

    return ret


def DFS(token, level=0):
    ret = dict()
    if isinstance(token, AST.Token):
        ret['type'] = 'array'
        ret['identifier'] = token.identifier
        ret['col_s'] = token.col_s
        ret['col_e'] = token.col_e
        ret['dim'] = token.dim
        ret['children'] = [DFS(x, level + 1) for x in token.children]
    elif isinstance(token, tuple):
        ret['type'] = 'tuple'
        ret['value'] = str(token)

    return ret


@app.route("/", methods=['POST'])
def parse_ast():
    j = flask.request.get_json()
    predefined = None
    if 'code' not in j:
        flask.abort(404)

    if 'predefined' in j:
        predefined = get_predefined(j['predefined'])

    node = AST.parse(j['code'])

    DV = AST.DimensionVisitor(predefinedFunc=all_func_dict, predefined=predefined)
    LV = AST.LocationVisitor(predefinedFunc=all_func_dict, predefined=predefined)

    result = dict()
    DV.result = result
    LV.result = result

    try:
        DV.visit(node)
        LV.visit(node)
        # insert_record(result)
        ret = dict({
            'status': 'ok',
            'result': DFS(result[node])
        })
    except Exception as e:
        ret = dict({
            'status': 'failed',
            'result': str(e)
        })

    return json.dumps(ret)

if __name__ == "__main__":
    app.run()
