# -*- coding: utf-8 -*-

import base64

from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.addons.base.res.res_bank import sanitize_account_number

import logging
_logger = logging.getLogger(__name__)



class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"
    _description = 'Import Bank Statement CSV format OKO Finland'

    #data_file = fields.Binary(string='Bank Statement File', required=True, help='Get you bank statements in electronic format from your bank and select them here.')

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
                transactions.append(
                    {
                    'name':other_part,
                    'date':accdate,
                    'amount': amountEUR,
                    'unique_import_id':archiveid,
                    'account_number':transaccount_and_bic,
                    'note':memo,
                    'partner_name':other_part,
                    'ref':referencecode,
                    'transtype':transtype,
                    'transdescr':transdescr
                }                    
                )
            else:
                header_skipped=True
            linenum=linenum+1
        # OKO csv does not include account number so we get it from journal
        journal_obj = self.env['account.journal']
        journal = journal_obj.browse(self.env.context.get('journal_id', []))
        account=journal.bank_account_id.sanitized_acc_number        
        #xname=_("OKO ")+mindate+" - "+maxdate
        return ("EUR",account,[{'date':maxdate,'transactions':transactions},])
        
    