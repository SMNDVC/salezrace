FROM odoo:16.0
USER root
RUN pip install werkzeug==2.0.3
COPY ./addons/odoo-llm/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN pip install jsonref