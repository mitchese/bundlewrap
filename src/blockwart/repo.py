from os import listdir
from os.path import isdir, isfile, join

from .exceptions import NoSuchGroup, NoSuchNode, RepositoryError
from .group import Group
from .node import Node
from .utils import cached_property, getattr_from_file, names, \
    mark_for_translation as _, validate_name

DIRNAME_BUNDLES = "bundles"
DIRNAME_ITEM_TYPES = "configitems"
FILENAME_GROUPS = "groups.py"
FILENAME_NODES = "nodes.py"

INITIAL_CONTENT = {
    FILENAME_GROUPS: _("""
groups = {
    #'group1': {
    #    'subgroups': (
    #        'group2',
    #    ),
    #    'bundles': (
    #        'bundle1',
    #    ),
    #    'nodes': (
    #        'node1',
    #    ),
    #},
    'all': {
    },
}

# node names matching these regexes
# will be added to the corresponding groups
group_patterns {
    r".*": "all",
}
    """),

    FILENAME_NODES: _("""
nodes = {
    'node1': {
        'hostname': "localhost",
        #'ssh_username': "jdoe",
    },
}
    """),
}


class Repository(object):
    def __init__(self, repo_path, skip_validation=False):
        self.path = repo_path

        self.bundles_dir = join(self.path, DIRNAME_BUNDLES)
        self.configitems_dir = join(self.path, DIRNAME_ITEM_TYPES)
        self.groups_file = join(self.path, FILENAME_GROUPS)
        self.nodes_file = join(self.path, FILENAME_NODES)

        if not skip_validation and not self.is_repo(repo_path):
            raise RepositoryError(
                _("'{}' is not a blockwart repository").format(self.path)
            )

    @staticmethod
    def is_repo(path):
        """
        Validates whether the given path is a blockwart repository.
        """
        try:
            assert isdir(path)
            assert isfile(join(path, "nodes.py"))
            assert isfile(join(path, "groups.py"))
        except AssertionError:
            return False
        return True

    @cached_property
    def bundle_names(self):
        """
        Returns the names of all bundles in this repository.
        """
        for dir_entry in listdir(self.bundles_dir):
            if validate_name(dir_entry):
                yield dir_entry


    def create(self):
        """
        Sets up initial content for a repository.
        """
        for filename, content in INITIAL_CONTENT.iteritems():
            with open(join(self.path, filename), 'w') as f:
                f.write(content.strip() + "\n")

    def get_group(self, group_name):
        try:
            return self.group_dict[group_name]
        except KeyError:
            raise NoSuchGroup(group_name)

    def get_node(self, node_name):
        try:
            return self.node_dict[node_name]
        except KeyError:
            raise NoSuchNode(node_name)

    @cached_property
    def group_dict(self):
        try:
            flat_group_dict = getattr_from_file(
                self.groups_file,
                'groups',
            )
        except KeyError:
            raise RepositoryError(
                _("{} must define a 'nodes' variable").format(
                    self.groups_file,
                )
            )
        groups = {}
        for groupname, infodict in flat_group_dict.iteritems():
            if groupname in names(self.nodes):
                raise RepositoryError(_("you cannot have a node and a group "
                                        "both named '{}'").format(groupname))
            groups[groupname] = Group(self, groupname, infodict)
        return groups

    @property
    def groups(self):
        result = list(self.group_dict.values())
        result.sort()
        return result

    def groups_for_node(self, node):
        for group in self.groups:
            if node in group.nodes:
                yield group

    @cached_property
    def node_dict(self):
        try:
            flat_node_dict = getattr_from_file(
                self.nodes_file,
                'nodes',
            )
        except KeyError:
            raise RepositoryError(
                _("{} must define a 'nodes' variable").format(
                    self.nodes_file,
                )
            )
        nodes = {}
        for nodename, infodict in flat_node_dict.iteritems():
            nodes[nodename] = Node(self, nodename, infodict)
        return nodes

    @property
    def nodes(self):
        result = list(self.node_dict.values())
        result.sort()
        return result
