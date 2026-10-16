"""Per-task SSH identity, propagated into worker threads without mutating shared tools."""
import contextvars,re,shlex
SHELL_IDENTITY=contextvars.ContextVar('kei_shell_identity',default=None)

def prepare_ssh(profile,secrets,command,sudo=True):
    identity=SHELL_IDENTITY.get();user=str(profile.get('user',''))
    if identity=='host_user':
        if user.casefold() in ('root','administrator'):raise PermissionError('Host User cần tài khoản SSH thường, không phải root/Administrator.')
        if re.search(r'\b(?:sudo|su|doas|runuser|pkexec)\b',command,re.I):raise PermissionError('Host User không tự nâng quyền. Chọn Full Machine · Root nếu được cấp quyền.')
        return 'test "$(id -u)" -ne 0 || exit 77; '+command,None,False
    if identity=='machine':
        command='test "$(id -u)" -eq 0 || exit 77; '+command
        if user=='root':return command,None,False
        elevation=profile.get('elevation','sudo')
        if elevation=='su':
            password=secrets.get(profile.get('root_password'))
            if not password:raise PermissionError('Cơ chế su cần root_password được lưu riêng trên host.')
            return 'stty -echo; exec su -s /bin/sh -c '+shlex.quote(command)+' root',password,True
        if elevation!='sudo' or profile.get('sudo',True) is False:raise PermissionError('Host chưa cấu hình cơ chế nâng quyền root cho tài khoản SSH này.')
        password=secrets.get(profile.get('password'))
        return ('sudo -S -p "" ' if password else 'sudo -n ')+'sh -c '+shlex.quote(command),password,False
    password=secrets.get(profile.get('password'))
    if sudo and profile.get('sudo',True):return ('sudo -S -p "" ' if password else 'sudo -n ')+'sh -c '+shlex.quote(command),password,False
    return command,None,False
