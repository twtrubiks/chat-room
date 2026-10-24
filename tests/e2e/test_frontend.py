import io
import os
import re

from PIL import Image
from playwright.sync_api import expect

TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')


def message_texts(page):
    # 訊息文字是 .message 的直屬文字節點（頭像與時間戳記是子元素）
    return page.eval_on_selector_all(
        '.messages-content .message',
        'els => els.map(el => [...el.childNodes].filter(n => n.nodeType === Node.TEXT_NODE)'
        '.map(n => n.textContent).join("").trim())',
    )


class TestLoginPage:
    def test_empty_form_is_not_submitted(self, new_page):
        page = new_page()
        page.goto('/login')

        page.click('button[type=submit]')

        expect(page.locator('form')).to_have_class(re.compile(r'\bwas-validated\b'))
        expect(page.get_by_text('Please enter a username.')).to_be_visible()
        assert page.url.endswith('/login')

    def test_login(self, login_page):
        page = login_page('alice')
        expect(page.locator('.chat-title h1')).to_have_text('alice')


class TestLogout:
    def test_logout_button(self, login_page):
        page = login_page('alice')

        page.click('.logout-button')

        # 登出後導回首頁，因為已經沒登入，會再被轉到登入頁
        page.wait_for_url('**/login?next=*')
        expect(page.locator('#username')).to_be_visible()
        page.goto('/index')
        page.wait_for_url('**/login?next=*')


class TestRegisterPage:
    def test_existing_username_blocks_submit(self, new_page, make_user, get_user):
        make_user('alice')
        page = new_page()
        page.goto('/register')

        page.fill('#username', 'alice')
        page.fill('#password', 'pw123')  # 離開帳號欄位會觸發檢查
        expect(page.locator('#usernameFeedback')).to_have_text('UserName already exists.')

        page.click('button[type=submit]')

        # Bootstrap 在表單 was-validated 之後才顯示 invalid-feedback
        expect(page.locator('#usernameFeedback')).to_be_visible()
        assert page.url.endswith('/register')
        assert get_user('alice').check_password('secret')

    def test_enter_in_username_field_still_checks(self, new_page, make_user, get_user):
        # 最後才填帳號、直接按 Enter：沒有 blur，只能靠送出前的檢查擋下來
        make_user('alice')
        page = new_page()
        page.goto('/register')
        page.fill('#password', 'pw123')
        page.fill('#username', 'alice')

        page.press('#username', 'Enter')

        expect(page.locator('#usernameFeedback')).to_have_text('UserName already exists.')
        expect(page.locator('#usernameFeedback')).to_be_visible()
        assert get_user('alice').check_password('secret')

    def test_submit_right_after_typing_taken_name(self, new_page, make_user):
        # 點 Register 時 blur 跟 submit 幾乎同時觸發檢查，送出前必須等檢查結果回來
        make_user('alice')
        page = new_page()
        page.goto('/register')
        posts = []
        page.on('request', lambda r: posts.append(r.url) if r.method == 'POST' and r.url.endswith('/register') else None)
        page.fill('#password', 'pw123')
        page.fill('#username', 'alice')

        page.click('button[type=submit]')

        expect(page.locator('#usernameFeedback')).to_have_text('UserName already exists.')
        expect(page.locator('#usernameFeedback')).to_be_visible()
        assert posts == []

    def test_changing_back_to_taken_name_is_checked_again(self, new_page, make_user):
        make_user('alice')
        page = new_page()
        page.goto('/register')
        page.fill('#username', 'alice')
        page.fill('#password', 'pw123')
        expect(page.locator('#usernameFeedback')).to_have_text('UserName already exists.')

        page.fill('#username', 'alicex')
        page.fill('#username', 'alice')
        page.focus('#password')

        expect(page.locator('#usernameFeedback')).to_have_text('UserName already exists.')

    def test_stale_check_result_is_ignored(self, new_page, make_user, get_user):
        make_user('alice')
        page = new_page()
        page.goto('/register')
        held = []

        def hold_first_check(route):
            if held:
                route.continue_()
            else:
                held.append(route)

        page.route('**/API_check_UserNameExist', hold_first_check)
        page.fill('#username', 'alice')
        page.fill('#password', 'pw123')  # 'alice' 的檢查被攔住，還沒回來
        while not held:
            page.wait_for_timeout(50)

        page.fill('#username', 'bob')
        with page.expect_request_finished(lambda r: 'API_check_UserNameExist' in r.url):
            page.focus('#password')
        # 'bob' 檢查完之後，'alice' 的舊結果才回來，不能把 'bob' 標成已被使用
        with page.expect_request_finished(lambda r: 'API_check_UserNameExist' in r.url):
            held[0].continue_()
        page.wait_for_timeout(300)
        expect(page.locator('#usernameFeedback')).to_have_text('Please enter a username.')

        page.click('button[type=submit]')
        page.wait_for_url('**/index')
        assert get_user('bob') is not None

    def test_editing_username_clears_error_and_registers(self, new_page, make_user, get_user):
        make_user('alice')
        page = new_page()
        page.goto('/register')
        page.fill('#username', 'alice')
        page.fill('#password', 'pw123')
        expect(page.locator('#usernameFeedback')).to_have_text('UserName already exists.')

        page.fill('#username', ' bob ')
        expect(page.locator('#usernameFeedback')).to_have_text('Please enter a username.')
        page.click('button[type=submit]')

        # 註冊後直接登入，帳號前後空白會被去掉
        page.wait_for_url('**/index')
        expect(page.locator('.chat-title h1')).to_have_text('bob')
        assert get_user('bob').check_password('pw123')


class TestChat:
    def test_messages_are_broadcast_escaped_and_persisted(self, login_page, wait_for_room):
        alice = login_page('alice', mugshot='alice.png')
        bob = login_page('bob', mugshot='bob.png')
        wait_for_room(2)

        alice.fill('.message-input', '<b>hi</b> bob')
        alice.press('.message-input', 'Enter')
        for page in (alice, bob):
            expect(page.locator('.messages-content .message')).to_have_count(1)
        expect(alice.locator('.message-input')).to_have_value('')

        bob.fill('.message-input', 'hello alice')
        bob.click('.message-submit')
        for page in (alice, bob):
            expect(page.locator('.messages-content .message')).to_have_count(2)
            assert message_texts(page) == ['<b>hi</b> bob', 'hello alice']
            # 使用者輸入的 HTML 不能被當成標籤
            expect(page.locator('.messages-content .message b')).to_have_count(0)
            expect(page.locator('.messages-content .message img').nth(0)).to_have_attribute(
                'src', '/static/mugshot/alice.png')
            expect(page.locator('.messages-content .message img').nth(1)).to_have_attribute(
                'src', '/static/mugshot/bob.png')
            for stamp in page.locator('.messages-content .timestamp').all_inner_texts():
                assert TIMESTAMP.match(stamp), stamp

        # 重新整理後，歷史訊息從 DB 讀出來，順序與內容一樣
        bob.reload()
        expect(bob.locator('.messages-content .message')).to_have_count(2)
        assert message_texts(bob) == ['<b>hi</b> bob', 'hello alice']

    def test_blank_and_shift_enter_are_not_sent(self, login_page, wait_for_room):
        alice = login_page('alice')
        wait_for_room(1)

        alice.fill('.message-input', '   ')
        alice.press('.message-input', 'Enter')
        alice.fill('.message-input', 'line one')
        alice.press('.message-input', 'Shift+Enter')
        alice.type('.message-input', 'line two')
        expect(alice.locator('.message-input')).to_have_value('line one\nline two')
        alice.press('.message-input', 'Enter')

        expect(alice.locator('.messages-content .message')).to_have_count(1)
        assert message_texts(alice) == ['line one\nline two']


class TestAvatarUpload:
    def test_crop_and_upload(self, login_page, make_image, get_user, mugshot_dir):
        page = login_page('alice')
        expect(page.locator('.chat-title .avatar img')).to_have_attribute('src', 'static/mugshot/default.jpg')

        page.click('.fa-gear')
        expect(page.locator('#CroppicModal')).to_be_visible()
        expect(page.locator('#cropConfirm')).to_be_disabled()
        page.set_input_files('#cropInput', files=[{
            'name': 'me.png',
            'mimeType': 'image/png',
            'buffer': make_image(size=(400, 300)).getvalue(),
        }])
        expect(page.locator('#cropConfirm')).to_be_enabled()
        page.click('#cropConfirm')

        # 上傳成功後頁面會重新整理，標題的頭像換成新檔名
        new_name = re.compile(r'^static/mugshot/[0-9a-f-]{36}\.png$')
        expect(page.locator('.chat-title .avatar img')).to_have_attribute('src', new_name)
        mugshot = get_user('alice').MugShot
        assert page.locator('.chat-title .avatar img').get_attribute('src') == 'static/mugshot/' + mugshot
        with open(os.path.join(mugshot_dir, mugshot), 'rb') as f:
            saved = Image.open(io.BytesIO(f.read()))
        # picture.js 會把選取範圍輸出成 256x256
        assert saved.size == (256, 256)
