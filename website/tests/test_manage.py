from manage import automigrate
from argparse import Namespace
from database_testing import DatabaseTest
from flask import current_app


class ManageTest(DatabaseTest):

    def test_automigrate(self):
        """Simple blackbox test for automigrate."""
        args = Namespace(databases=('bio', 'cms'))
        result = automigrate(args, current_app)
        assert result
