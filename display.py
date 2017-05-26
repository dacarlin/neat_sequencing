from flask import Markup

def html_status_codes( status_code, issue=0 ):
    st_code = str(status_code)
    mp = {
        0: {
            "codes": [
                # ('0','⚫ ⚪ ⚪ ⚪'),
                # ('1','⚪ ⚫ ⚪ ⚪'),
                # ('2','⚪ ⚪ ⚫ ⚪'),
                # ('3','⚪ ⚪ ⚪ ✅'),
                # ('0','●<span style="color:#aaa">●●●</span> <small><br>Order placed</small>'),
                # ('1','<span style="color:#aaa">●</span>●<span style="color:#aaa;">●●</span> <small><br>Plate shipped</small>'),
                # ('2','<span style="color:#aaa">●●</span>●<span style="color:#aaa;">●</span> <small><br>Plate received</small>'),
                # ('3','<span style="color:#aaa">●●●</span>● <small><br>Plate in work cell</small>'),
                ('0','●<span style="color:#aaa">●●●</span> <small><br>Order placed</small>'),
                ('1','<span style="color:#aaa">●</span>●<span style="color:#aaa;">●●</span> <small><br>Plate shipped</small>'),
                ('2','<span style="color:#aaa">●●</span>●<span style="color:#aaa;">●</span> <small><br>Plate received</small>'),
                ('3','<span style="color:#aaa">●●●</span>● <small><br>Plate in work cell</small>'),
            ]
        },
        1: {
            "codes": [
                ('0','🔴 ⚪ ⚪ ⚪'),
                ('1','⚪ 🔴 ⚪ ⚪'),
                ('2','⚪ ⚪ 🔴 ⚪'),
                ('3','⚪ ⚪ ⚪ 🔴'),
            ]
        }
    }

    codes = dict(mp[issue]["codes"])
    if st_code in codes.keys():
        return Markup('<span class="stat">' + codes[ st_code ] + '</span>')

def html_status_codes_human(status_code, plate_or_seq='plate'):

    mp = {
        'plate': {
            0: 'Plate ordered by you',
            1: 'Plate shipped to you',
            2: 'Plate used in sequencing order',
            3: 'Plate received by us'
        }
    }

    my_map = mp[plate_or_seq]
    return my_map[status_code]
