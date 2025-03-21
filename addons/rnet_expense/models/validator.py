from odoo.exceptions import ValidationError


class ExpenseValidator:
    def validate_pettycash(self, values):
        if values.get('transaction_type') == 'petty_cash' and values.get('journal_petty_cash') is False:
            raise ValidationError(
                'Untuk tipe transaksi cash advance, jurnal cash advance employee harus dipilih')
