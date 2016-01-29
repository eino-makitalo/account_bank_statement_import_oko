# -*- encoding: utf-8 -*-
{
    'name': 'Account Bank Statement Import OKO Finland',
    'category': 'Accounting & Finance',
    'version': '9.0.0.0.1',
    'depends': ['account_bank_statement_import'],
    'description': """OKO Bank simple bank statement in csv format""",
    'data': [
         'account_bank_statement_import_oko_view.xml',
    #    'account_bank_statement_import_view.xml',
    #    'account_import_tip_data.xml',
    #    'wizard/journal_creation.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': True,
}
