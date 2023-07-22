import dotenv
import os
from datetime import date


class autoRenewLetsEncrypt():

    def __init__(self):
        dotenv.load_dotenv(dotenv.find_dotenv())
        self.encryptLivePath = os.getenv('ENCRYPT_PATH') + '/live/' + os.getenv('DOMAIN')
        self.encryptArchivePath = os.getenv('ENCRYPT_PATH') + '/archive/' + os.getenv('DOMAIN')
        self.encryptRenewPath = os.getenv('ENCRYPT_PATH') + '/renew/' + os.getenv('DOMAIN') + '.conf'
        self.domain = os.getenv('DOMAIN')
        self.haproxyPath = os.getenv('HAPROXY_PATH')
        self.todayDate = date.today()

    def start(self):
        # if self.renewLetsEncrypt():
        #     if self.makeSitePem():
        #         if self.changeEncryptDirName():
        #             if self.modifyProxyConfig():
        #                 return True
        return False

    def renewLetsEncrypt(self):
        # Let's Encrypt 인증서 재발급
        command = "certbot certonly --dns-cloudflare --preferred-challenges dns-01 " \
                   "--dns-cloudflare-propagation-seconds 20 --dns-cloudflare-credentials " \
                   f"/root/.secrets/certbot-cloudflare.ini -d {self.domain} -d *.{self.domain}"

        if str(os.system(command)).find("Successfully received certificate."):
            return True

        return False

    def makeSitePem(self):
        # site.pem 파일 생성
        if os.system(f"cat {self.encryptLivePath}/cert.pem {self.encryptLivePath}/chain.pem {self.encryptLivePath}/privkey.pem > {self.encryptLivePath}/site.pem"):
            return True

        return False

    def changeEncryptDirName(self):
        # ========================================================================================
        # live, archive : mv {ENCRYPT_PATH}{DOMAIN} {ENCRYPT_PATH}{DOMAIN}-{당일날짜(YYYY-MM-DD)}
        # renew : mv {ENCRYPT_PATH}{DOMAIN}.conf {ENCRYPT_PATH}{DOMAIN}-{당일날짜(YYYY-MM-DD)}.conf
        # ========================================================================================

        # live, archive 디렉토리명 변경
        if os.system(f"mv {self.encryptLivePath}/ {self.encryptLivePath}-{self.todayDate}"):
            if os.system(f"mv {self.encryptArchivePath}/ {self.encryptArchivePath}-{self.todayDate}"):
                # renew 파일명 변경
                if os.system(f"mv {self.encryptRenewPath}/ {self.encryptRenewPath}-{self.todayDate}"):
                    return True

        return False

    def modifyProxyConfig(self):



        return "test"


if __name__ == '__main__':
    renewClass = autoRenewLetsEncrypt()
    if renewClass.start():
        print('성공')
    else:
        print('실패')
