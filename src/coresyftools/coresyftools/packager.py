#!/usr/bin/python2
import os
import glob
from os import mkdir, rename, listdir
from os.path import join, basename, splitext, exists
from shutil import copy, make_archive, move
from tool_tester import ToolTester
from manifest import get_manifest
import click


class ToolDirectoryNotFoundException(Exception):
    pass


class TargetDirectoryNotFoundException(Exception):
    pass


class MissingRunFileException(Exception):
    pass


class MissingManifestFileException(Exception):
    pass


class MissingExamplesFileException(Exception):
    pass

class MultipleManifestFileException(Exception):
    pass

class ToolErrorsException(Exception):

    def __init__(self, errors):
        self.errors = errors


class Packager():

    def __init__(self, tool_dir, target_dir, scihub_credentials):
        self.tool_dir = tool_dir
        self.target_dir = target_dir
        self.scihub_credentials = scihub_credentials
        self.manifest = None

    def _check_tool_directory_structure(self):
        if not exists(self.tool_dir):
            raise ToolDirectoryNotFoundException()
        if not exists(self.target_dir):
            raise TargetDirectoryNotFoundException()
        if not exists(join(self.tool_dir, 'run')):
            raise MissingRunFileException()
        manifest_files = self._find_manifest_files()
        if not manifest_files:
            raise MissingManifestFileException()
        if len(manifest_files) > 1:
            raise MultipleManifestFileException()
        if not exists(join(self.tool_dir, 'examples.sh')):
            raise MissingExamplesFileException()
    
    def _read_manifest(self):
        manifest_file_name = self._find_manifest_files()[0]
        self.manifest = get_manifest(manifest_file_name)
    
    def _find_manifest_files(self):
        return glob.glob(join(self.tool_dir, '*manifest.json'))

    def _test(self):
        tester = ToolTester(self.tool_dir, self.scihub_credentials)
        tester.test()
        if tester.errors:
            raise ToolErrorsException(tester.errors)

    def _archive(self):
        make_archive(join(self.target_dir, self.manifest['name']),
                     'zip', self.tool_dir)

    def pack_tool(self):
        self._check_tool_directory_structure()
        self._read_manifest()
        self._test()
        self._archive()


@click.command()
@click.option('--tool_dir', type=click.Path(), default='.')
@click.option('--target_dir', type=click.Path(), default='..')
@click.option('--scihub_user')
@click.option('--scihub_pass')
def pack_tool(tool_dir, target_dir, scihub_user, scihub_pass):
    click.echo('Packaging {} to {}..'.format(tool_dir, target_dir))
    packager = Packager(tool_dir, target_dir, (scihub_user, scihub_pass))
    packager.pack_tool()
    click.echo('Packaging finished.')

if __name__ == '__main__':
    pack_tool()
