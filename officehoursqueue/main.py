#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
from google.appengine.ext import ndb

# Models
class OfficeHour(ndb.Model):
    office_hours_id = ndb.StringProperty(required = True)

class StudentPost(ndb.Model):
    name = ndb.StringProperty(required = True)
    content = ndb.TextProperty(required = True)
    office_hours_id = ndb.StringProperty(required = True)
    created = ndb.DateTimeProperty(auto_now_add = True)

# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent. However, the write rate should be limited to
# ~1/second.
def office_hours_key(office_hours_id):
    """Constructs a Datastore key for a StudentPost entity.
    We use office_hours_id as the key.
    """
    return ndb.Key('StudentPost', office_hours_id)

# Template Directories
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)


# MainHandlerClass
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class OfficeHoursTakerHandler(Handler):
    """
    Handler for working for taking user to office hours page.
    """
    def render_form(self, error="", office_hours_id=""):
        self.render("newofficehours.html", error=error, office_hours_id=office_hours_id)

    def get(self):
        self.render_form()

    def post(self):
        # Get the office hours id from the form
        office_hours_id = self.request.get("office_hours_id")
        if office_hours_id is None:
            error = "Office Hours ID cannot be empty."
            self.render_form(error, office_hours_id)
        else:
            self.redirect('/{0}'.format(office_hours_id))


class QueueHandler(Handler):
    """
    Handler for displaying the front page of the queue for a given class
    """
    def render_queue(self, office_hours_id):
        query = "SELECT * FROM StudentPost \
                 WHERE ANCESTOR IS :ok \
                 ORDER BY created ASC"
        parent = office_hours_key(office_hours_id)
        posts = StudentPost.query(ancestor=office_hours_key(office_hours_id)).order(StudentPost.created)
        self.render("queue.html", office_hours_id=office_hours_id, posts=posts)

    def get(self, office_hours_id):
        self.render_queue(office_hours_id)


class PageHandler(Handler):
    """
    Handler for displaying unique pages for each queue post
    """
    def render_post(self, office_hours_id, posts="", post_id=""):
        self.render("post.html", office_hours_id=office_hours_id, posts=posts, post_id=post_id)

    def get(self, office_hours_id, post_id):
        posts = StudentPost.query(ancestor=office_hours_key(office_hours_id)).order(StudentPost.created)
        self.render_post(office_hours_id, posts, post_id)


class NewPostHandler(Handler):
    """
    Handler for working with new post form to create new queue posts
    """
    def render_form(self, name="", content="", error="", office_hours_id=""):
        self.render("newpost.html", name=name, content=content, 
                                    error=error, office_hours_id=office_hours_id)

    def get(self, office_hours_id):
        self.render_form(office_hours_id = office_hours_id)

    def post(self, office_hours_id):
        name = self.request.get("name")
        content = self.request.get("content")
        if name and content:
            parent = office_hours_key(office_hours_id)
            sp = StudentPost(parent = parent, name = name, content = content, office_hours_id = office_hours_id)
            sp.put()
            self.redirect('/{0}'.format(office_hours_id))
        else:
            error = "You need both a name and some content."
            self.render_form(name, content, error)


class DeleteHandler(Handler):
    """
    Handler for working with new post form to create new queue posts
    """
    def get(self, office_hours_id, post_id):
        # Delete a specific post - we are done.
        posts = StudentPost.query(ancestor=office_hours_key(office_hours_id)).order(StudentPost.created)
        for post in posts:
            if str(post.key.id()) == post_id:
                post.key.delete()
                break
        self.redirect('/{0}'.format(office_hours_id))


app = webapp2.WSGIApplication([
    ('/', OfficeHoursTakerHandler),
    ('/([a-zA-Z0-9_-]+)', QueueHandler),
    ('/([a-zA-Z0-9_-]+)/newpost', NewPostHandler),
    ('/([a-zA-Z0-9_-]+)/([0-9]+)', PageHandler),
    ('/([a-zA-Z0-9_-]+)/([0-9]+)/delete', DeleteHandler)
], debug=True)
