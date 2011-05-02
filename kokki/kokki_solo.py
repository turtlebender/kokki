from ConfigParser import SafeConfigParser
import optparse
import os
import logging
import json
from kokki import Kitchen
import re

recipe = re.compile('^recipe\[(.*)\]$')
role = re.compile('^role\[(.*)\]$')

def build_parser():
    parser = optparse.OptionParser()
    parser.add_option('-c', action="store", dest="config", default=os.path.expanduser('~/.kokki.cfg'))
    parser.add_option('-j', action="store", dest="json", default=os.path.join(os.getcwd(), 'node.json'))
    parser.add_option('-v', action='store_true', dest='verbose', default=False)
    return parser

def process_role_file(kit, json_role, file_cache_path):
    fp = open(os.path.join(file_cache_path, 'roles', json_role))
    try:
        role = json.load(fp)
        process_role(kit, role, file_cache_path)
    finally:
        fp.close()



def process_role(kit, descriptor, file_cache_path):
    for run_item in descriptor['run_list']:
        recipe_match = recipe.match(run_item)
        if recipe_match:
            kit.include_recipe(recipe_match.group(1))
            continue
        role_match = role.match(run_item)
        if role_match:
            process_role_file(kit, '%s.json' % role_match.group(1), file_cache_path)
    kit.config.update(descriptor['data'])

def main():
    parser = build_parser()
    options, args = parser.parse_args()

    if not args and not options.config:
        parser.error("must specify at least one command")

    logging.basicConfig(level=logging.INFO)
    if options.verbose:
        logger = logging.getLogger('kokki')
        logger.setLevel(logging.DEBUG)
    config_file = options.config
    parser = SafeConfigParser()
    parser.read(config_file)
    if not parser.has_option('kokki', 'file_cache_path'):
        print "Must specify file_cache_path in config file"
        return -1
    file_cache_path = parser.get('kokki', 'file_cache_path')
    if not parser.has_option('kokki', 'cookbook_path'):
        print "Must specify cookbook_path in the config file"
        return -1
    cookbook_path = parser.get('kokki', 'cookbook_path')

    json_descriptor_path = options.json
    if not os.path.exists(json_descriptor_path):
        print "Node descriptor file required"
        return -1
    fp = open(json_descriptor_path)
    try:
        descriptor = json.load(fp)
    finally:
        fp.close()
    kit = Kitchen()
    kit.add_cookbook_path(cookbook_path)
    process_role(kit, descriptor, file_cache_path)
    kit.run()

if __name__ == "__main__":
    main()

