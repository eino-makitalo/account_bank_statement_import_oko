# -*- coding: utf-8 -*-

import base64

from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.addons.base.res.res_bank import sanitize_account_number
from decimal import Decimal
import openerp.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)



class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"
    _description = 'Import Bank Statement CSV format OKO Finland'

    #data_file = fields.Binary(string='Bank Statement File', required=True, help='Get you bank statements in electronic format from your bank and select them here.')
    balance_start = fields.Float(
        'Starting Balance',
        digits_compute=dp.get_precision('Account')
    )

    bank_statement_date = fields.Date(
        'Bank Statement Date',
        help="You can choose to manually set the bank statement date here. "
             "Otherwise the bank statement date will be read from the latest "
             "bank statement line date ",
    )



    OKO_START_ROW="Kirjauspäivä;Arvopäivä;Määrä EUROA;Laji;Selitys;Saaja/Maksaja;Saajan tilinumero ja pankin BIC;Viite;Viesti;Arkistointitunnus".decode("utf-8").encode("iso8859-1")
    def __check_oko(self,data_file):        
        """ Check if it's OKO Tositetiliote format  csv """
        return (data_file[:len(self.OKO_START_ROW)]==self.OKO_START_ROW)
        
    def _parse_file(self, data_file):        
        """ Each module adding a file support must extends this method. It processes the file if it can, returns super otherwise, resulting in a chain of responsability.
            This method parses the given file and returns the data required by the bank statement import process, as specified below.
            rtype: triplet (if a value can't be retrieved, use None)
                - currency code: string (e.g: 'EUR')
                    The ISO 4217 currency code, case insensitive
                - account number: string (e.g: 'BE1234567890')
                    The number of the bank account which the statement belongs to
                - bank statements data: list of dict containing (optional items marked by o) :
                    - 'name': string (e.g: '000000123')
                    - 'date': date (e.g: 2013-06-26)
                    -o 'balance_start': float (e.g: 8368.56)
                    -o 'balance_end_real': float (e.g: 8888.88)
                    - 'transactions': list of dict containing :
                        - 'name': string (e.g: 'KBC-INVESTERINGSKREDIET 787-5562831-01')
                        - 'date': date
                        - 'amount': float
                        - 'unique_import_id': string
                        -o 'account_number': string
                            Will be used to find/create the res.partner.bank in odoo
                        -o 'note': string
                        -o 'partner_name': string
                        -o 'ref': string
        """
        if not self.__check_oko(data_file):
            return super(AccountBankStatementImport, self)._parse_file(data_file)            
        
        transactions=[]
        mindate="9999-99-99"
        maxdate="0000-00-00"
        total_amt = Decimal(0) 
        header_skipped=False
        linenum=1
        for row in data_file.split("\n"):
            if header_skipped:
                row=row.strip().decode("iso8859-15").encode("utf-8")
                fields=row.split(";")
                if row=='':
                    continue;
                if (len(fields)!=10):
                    raise UserError(_('OKO Bank CSV file (tositetiliote) included wrong number of fields. Expected 10 got %d\nLine %d:%s') % (len(fields),linenum,row))
                accdate,valuedate,amountEUR,transtype,transdescr,other_part,transaccount_and_bic,referencecode,memo,archiveid=fields
                d,m,y=accdate.split(".")
                amountEUR=float(amountEUR.replace(",","."))
                accdate="%04d-%02d-%02d"%(int(y),int(m),int(d))
                if accdate<mindate:
                    mindate=accdate
                if accdate>maxdate:
                    maxdate=accdate

                #Mikulta
                # The last part is just the bank identifier
                identifier = transaccount_and_bic.rfind(' ')
                acc_num=transaccount_and_bic[:identifier]
                if len(memo.strip())==0:
                    memo='-'
                if len(other_part.strip())==0:
                    other_part=''
                oneval={
                    'sequence': linenum, # added for sequence?
                    'name':other_part,
                    'date':accdate,
                    'amount': amountEUR,
                    'unique_import_id':archiveid+"-"+accdate,
                    'account_number':acc_num,
                    'note':memo,
                    'partner_name':other_part,
                    'ref':referencecode,
                }
                transactions.append(oneval)
                
                total_amt = total_amt + Decimal(amountEUR)
                linenum=linenum+1  # advance sequence                
            else:
                header_skipped=True
        # OKO csv does not include account number so we get it from journal
        journal_obj = self.env['account.journal']
        journal = journal_obj.browse(self.env.context.get('journal_id', []))
        balance_end=Decimal(self.balance_start)+total_amt
        
        account=journal.bank_account_id.sanitized_acc_number        
        vals_bank_statement = {
            'balance_start': self.balance_start,
            'balance_end_real': balance_end,
            'date': self.bank_statement_date if self.bank_statement_date else maxdate,
            'transactions': transactions
        }        
        return ("EUR",account,[vals_bank_statement,])
        
    