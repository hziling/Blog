# -*- coding: utf-8 -*-
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash
from flask.ext.login import login_user, logout_user, login_required, current_user
from . import auth
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, ChangeEmailForm
from .. import db
from ..models import User
from ..email import send_email

# @main.route('/', methods=['GET', 'POST'])
# def index():
#     # form = NameForm()
#     if form.validate_on_submit():
#         return redirect(url_for('.index'))
#     return render_template('index.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)  # 是否记录登录状态
            # request.args.get('next')会记录上次的页面
            return redirect(request.args.get('next') or url_for('main.index'))
        flash(u'用户名或密码错误！')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash(u'退出登录！')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, u'确认您的账户', 'auth/email/confirm',
                   user=user, token=token)
        flash(u'邮件已经发送到您的邮箱，请点击确认您的账户！')
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash(u'您已经确认了您的账户！')
    else:
        flash(u'确认链接已经失效')
    return redirect(url_for('main.index'))


# 用户已登录， 用户账户未确认， 不在认证路由中 会拦截请求
@auth.before_app_request
def before_request():
    if current_user.is_authenticated():
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous() or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, u'确认您的账户',
               'auth/email/confirm', user=current_user, token=token)
    flash(u'一封邮件已经发送到您的邮箱！')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash(u'您已经修改了您的密码！')
            redirect(url_for('main.index'))
        else:
            flash(u'密码错误')
    return render_template('auth/change_password.html', form=form)


@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, u'确认您的邮箱',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash(u'一封邮件已经发送到您的邮箱！')
            return redirect(url_for('main.index'))
        else:
            flash(u'密码错误')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
       flash(u'邮箱已经更新')
    else:
        flash(u'无效的请求')
    return redirect(url_for('main.index'))