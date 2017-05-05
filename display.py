from flask import Markup

def html_status_codes( status_code, issue=0 ):
    st_code = str(status_code)
    codes = [
        ('0','⚫⚪⚪⚪'),
        ('1','⚪⚫⚪⚪'),
        ('2','⚪⚪⚫⚪'),
        ('3','⚪⚪⚪⚫'),
        # ('0','●<span style="color:#aaa">●●●</span> <small><br>Order placed</small>'),
        # ('1','<span style="color:#aaa">●</span>●<span style="color:#aaa;">●●</span> <small><br>Plate shipped</small>'),
        # ('2','<span style="color:#aaa">●●</span>●<span style="color:#aaa;">●</span> <small><br>Plate received</small>'),
        # ('3','<span style="color:#aaa">●●●</span>● <small><br>Plate in work cell</small>'),
    ]
    codes = dict(codes)
    if st_code in codes.keys():
        return Markup(codes[ st_code ])
