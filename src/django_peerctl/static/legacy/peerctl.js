(function($, tc) {

// using jQuery
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

Peerctl = {};

Peerctl.util = {

  /**
   * sort an array of objects by their key value
   *
   * @function sort
   * @param {Array} array
   * @param {string} key
   * @param {bool} reverse
   * @returns {Array} sorted array
   */
  "sort" : function(array, key, reverse) {
    array.sort(function(a,b) {
      var a_v = (a[key] || "").toLowerCase();
      var b_v = (b[key] || "").toLowerCase();
      if(a_v < b_v) return reverse ? 1 : -1;
      if(a_v > b_v) return reverse ? -1 : 1;
      return 0;
    });
    return array;
  },

  "choice_label" : function(choices, value) {
    var i;
    for(i = 0; i< choices.length; i++) {
      if(choices[i].value == value)
        return choices[i].display_name;
    }
    return value;
  },

  "url_anchor" : function(handler=function(a){return a;}) {
    var url = document.location.href;
    return handler(url.substring(url.indexOf("#")+1));
  },

  "url_anchor_asn" : function() {
    return this.url_anchor(function(anchor) {
      if(anchor.indexOf("-") > -1) {
        return parseInt(anchor.split("-")[0]);
      } else {
        return parseInt(anchor);
      }
    });
  },

  "url_anchor_page" : function() {
    return this.url_anchor(function(anchor) {
      if(anchor.indexOf("-") > -1) {
        return anchor.split("-")[1];
      }
      return null;
    });
  },

  "url_param" : function(name, handler=function(a){return a;}) {
    var url = decodeURIComponent(window.location.search.substring(1)),
        params = url.split('&'),
        param_name, i;

    for (i = 0; i < params.length; i++) {
        param_name = params[i].split('=');
        if (param_name[0] === name) {
            return param_name[1] === undefined ? true : handler(param_name[1]);
        }
    }
  },

  "menu_label" : function(label, glyphicon) {
    if(typeof label == "string")
      label = $('<span>').text(label);

    if(glyphicon) {
      $('<span> </span>').prependTo(label);
      $('<span>').addClass("glyphicon glyphicon-"+glyphicon).
      prependTo(label);
    }
    return label;
  },

  "copy_to_clipboard" : function(element) {
    element.select();
    document.execCommand("copy");
  }
};

/**
 * Return a jquery node for an error message
 *
 * This can either be passed a plain error message string or
 * an array containing 2 elements
 *
 * When an array is passed it will look for a more detailed
 * error template to use.
 *
 * The first element in the array is used to locate the template.
 * The second element in the array is the error message string
 *
 * @method errmsg_node
 * @param {String|Array} errmsg
 * @returns {jQuery}
 */

Peerctl.errmsg_node = function(errmsg) {
  if(errmsg.push) {
    var node = peerctl.elements["error_"+errmsg[0]]
    if(node.length) {
      node = node.clone()
      node.find('.errmsg').text(errmsg[1])
      return node;
    } else {
      return $('<div>').text(errmsg[1])
    }
  } else {
    return $('<div>').text(errmsg)
  }
}



Peerctl.util.Timeout = twentyc.cls.extend(
  "Timeout",
  {
    "Timeout" : function(callback, interval) {
      if(callback)
        this.set(callback, interval);
      $(this).on("done", function() {
        this._timeout = null;
      }.bind(this));
    },
    "active" : function() {
      return (this._timeout != null);
    },
    "ready" : function(callback) {
      if(!this.active())
        callback();
      else {
        $(this).one("done", callback);
      }
    },
    "set" : function(callback, interval) {
      var _callback = function() {
        callback();
        $(this).trigger("done");
      }.bind(this)
      this.SmartTimeout_set(_callback, interval);
    }
  },
  twentyc.util.SmartTimeout
);

/**
 * Collection of field formatters
 *
 * @class formatters
 * @namespace Peerctl
 */

Peerctl.formatters = {

  /**
   * Format network speed
   *
   * @method speed
   * @param {Number} value - speed in bytes
   * @returns {String}
   */
  "speed" : function(value, api_object) {
    value = parseInt(value);
    if(value >= 1000000)
      value = (value / 1000000)+"T";
    else if(value >= 1000)
      value = (value / 1000)+"G";
    else
      value = value+"M";
    return value
  },

  "peeringdb" : function(value, api_object) {
    return $('<span>').append(
      $('<img>').prop("src", Peerctl.STATIC_URL+"peeringdb.ico").
      addClass("icon16 marg-right-xs")
    ).append(
      $('<a>').prop("href", api_object.peeringdb).text(value)
    );
  },

  "device_name" : function(value, api_object) {
    if(value.match(/^member(\d+)$/)) {
      return api_object.display_name;
    }
    return value;
  },

  "policy" : function(value, api_object) {
    var r = $('<span>');
    if(value) {
      if(value.inherited) {
        r.addClass("policy-inherited");
      }
      r.text(value.name);
    } else {
      r.text('-');
    }

    return r;
  }
}


// for convenience
var $util = Peerctl.util;
var $fmt = Peerctl.formatters;

/**
 * Handles requests to the peerctl
 * API
 * @class API
 * @namespace Peerctl
 * @param {string} base_url - the base path of the api (eg. /api)
 */

Peerctl.API = tc.cls.define(
  "API",

  {
    "API" : function(base_url) {
      this.base_url = base_url;
    },

    /**
     * Returns an error handler to use for ajax requests
     * to the api
     *
     * The callback function accepts three arguments
     *
     *     - response: the request response object
     *     - errors: array of errors
     *     - data: array of data
     *
     * @method error_handler
     * @param {Function} callback
     * @returns {Function}
     */

    "error_handler" : function(callback) {
      return function(response) {
        var b, i;
        var data = response.responseJSON;
        var errors = [];

        if(data && data.errors) {
          var value;
          for(i in data.errors) {
            value = data.errors[i]
            if(typeof(value) != "object")
              value = [value];
            errors.push({name:i, value:value});
          }
        }

        if(callback)
          b = callback(response, errors, data)
        if(b)
          return;
      }
    },

   /**
     * Creates an error handler for API responses
     *
     * The callback function accepts these arguments:
     *
     *     - response: request response object
     *     - errors: array of errors
     *     - data: array of data
     *
     * @method error_display
     * @param {jQuery} element
     */

    "error_display_handler" : function(element) {
      this.clear_rendered_errors(element)

      var callback = function(response, errors, data) {

        if(!element || !element.length) {
          var element = this.show_error_modal()
        }

        if(!errors.length) {
          if(response.status == 403) {
            errors.push({name:"non_field_errors", value:["Permission Denied"]});
          } else if(response.statusCode == 401) {
            errors.push({name:"non_field_errors", value:["Authentication Required"]});
          } else {
            errors.push({name:"non_field_errors", value:[response.status+" Server error"]});
          }
        }
        $(errors).each(function() {
          var par = element.find('[name="'+this.name+'"]').parents('.element-group');
          par.addClass('has-error has-feedback');
          $('<span class="help-block validation-error">').text(this.value).appendTo(par)
          $('<span class="glyphicon glyphicon-remove validation-error element-control-feedback">').appendTo(par)

          if(this.name == "non_field_errors" || this.name == "detail") {
            var i, misc = $('<div class="panel panel-default"><div class="panel-body bg-danger validation-error"></div></div>');

            for(i in this.value) {
              $('<p>').appendTo(misc.find('.panel-body')).append(
                Peerctl.errmsg_node(this.value[i])
              );
            }

            element.prepend(misc)
          }
        });
      }.bind(this)
      return this.error_handler(callback);
    },

    "show_error_modal" : function() {
      var body = $('<div>')
      var modal = new Peerctl.Modals.Base(
        peerctl.elements.modal_display.clone(),
        "Server Error",
        body);
      modal.show();
      return body;
    },

    /**
     * Returns a data handler to use to process data
     * retrieved from ajax requests to the api
     *
     * The callback function accepts two arguments
     *
     *     - data: array of data provided in the api response at the "data" key
     *     - full: complete object returned by api response
     *
     * @method data_handler
     * @param {Function} callback
     * @returns {Function}
     */

    "data_handler" : function(callback, single, sent_data) {
      return function(data) {
        if(!data) {
          data = {data:[]}
        }
        var r= single ? data.data[0] : data.data;
        if(callback)
          callback(r, data, sent_data);
      }
    },

    /**
     * Returns a meta handler to use to process meta data
     * retrieved from ajax requests to the api
     *
     * @method meta_handler
     * @param {Function} callback
     *
     *     Arguments:
     *
     *     - meta: meta data object
     *     - full: complete object returned by api response
     *
     * @returns {Function}
     */

    "meta_handler" : function(callback) {
      return function(data) {
        var _data = data.data[0];
        if(!_data.actions)
          _data.actions = {}
        var meta = {
          fields : (_data.actions.POST || {})
        };

        if(callback)
          callback(meta, data)
      }
    },

    "data" : function(data) {
      if(!data)
        data = {}
      return data
    },

    "clear_rendered_errors" : function(element) {
      element.prev(".validation-error").detach();
      element.find(".validation-error").detach();
    },

    /**
     * Retrieve an objects from the api
     *
     * @method retrieve
     * @param {String} path: the api path without the base url
     * @param {Object} param: request url parameters
     * @param {Function} success
     * @param {Function} error
     */

    "retrieve" : function(path, param, success, error, render_errors_to) {

      var request = $.ajax({
        url : this.base_url+"/"+path,
        method : "GET",
        data : param || {},
        success : this.data_handler(success, true, param || {})
      }).fail(this.error_handler(error));

      if(render_errors_to)
        request.fail(this.error_display_handler(render_errors_to));
    },


    /**
     * Retrieve a list of objects from the api
     *
     * @method list
     * @param {String} path: the api path without the base url
     * @param {Object} param: request url parameters
     * @param {Function} success
     * @param {Function} error
     */

    "list" : function(path, param, success, error, render_errors_to) {
      var request = $.ajax({
        url : this.base_url+"/"+path,
        method : "GET",
        data : param || {},
        success : this.data_handler(success, false, param || {})
      }).fail(this.error_handler(error));

      if(render_errors_to)
        request.fail(this.error_display_handler(render_errors_to));
    },

    /*
     * Create an object
     *
     * @method create
     * @param {String} path: the api path without the base url
     * @param {Object} data: object data
     * @param {Function} success
     * @param {Function} error
     */

    "create" : function(path, data, success, error, render_errors_to) {
      var request = $.ajax({
        url : this.base_url+"/"+path,
        method : "POST",
        data : this.data(data),
        success : this.data_handler(success, false, data || {})
      }).fail(this.error_handler(error));

      if(render_errors_to)
        request.fail(this.error_display_handler(render_errors_to));
    },

    /*
     * Update an object
     *
     * @method create
     * @param {String} path: the api path without the base url
     * @param {Object} data: object data
     * @param {Function} success
     * @param {Function} error
     */


    "update" : function(path, data, success, error, render_errors_to) {
      var request = $.ajax({
        url : this.base_url+"/"+path,
        method : "PUT",
        data : this.data(data),
        success : this.data_handler(success, false, data || {})
      }).fail(this.error_handler(error));

      if(render_errors_to)
        request.fail(this.error_display_handler(render_errors_to));
    },

    /*
     * Delete an object
     *
     * @method create
     * @param {String} path: the api path without the base url
     * @param {Function} success
     * @param {Function} error
     */

    "delete" : function(path, success, error, render_errors_to) {
      var request = $.ajax({
        url : this.base_url+"/"+path,
        method : "DELETE",
        success : this.data_handler(success, false, {})
      }).fail(this.error_handler(error));

      if(render_errors_to)
        request.fail(this.error_display_handler(render_errors_to));
    },

    /*
     * Load meta data of an api endpoint
     *
     * @method meta
     * @param {String} path: the api path without the base url
     * @param {Function} success
     * @param {Function} error
     */

    "meta" : function(path, success, error) {
      $.ajax({
        url : this.base_url+"/"+path,
        method : "OPTIONS",
        success : this.meta_handler(success)
      }).fail(this.error_handler(error));
    },

    /**
     * Creates a deferred request function that can be called
     * whenever you are read to send the request
     *
     * @method deferred_request
     * @param {Object} config
     *
     *     - path (function): should return path on the api you want to request
     *     - data (function): should return object of data/params you want to send
     *     - success (function): success handler
     *     - error (function): error_handler
     *     - render_errors_to (jQuery): errors will be rendered to this element
     *
     *     The `path` and `data` function will passed whatever parameter
     *     you pass to the request function when you call it.
     */

    "deferred_request" : function(config) {
      var send_request = function(extra) {
        var success = null, error = null;
        if(typeof config.success == "function")
          success = config.success.bind(extra);
        if(typeof config.error == "function")
          error = config.error.bind(extra);

        // show confirmation
        if(config.confirm) {
          var c = confirm(config.confirm)
          if(!c) {
            return;
          }
        }

        // show loading shim if it is set
        if(typeof config.show_loading_shim == "function")
          config.show_loading_shim(extra);

        // success callback handler
        var _success = function(a,b,c) {

          // call the custom success callback if
          // it is set
          if(success) {
            success(a,b,c,extra)
          }

          // hide the loading shim if it
          // is set
          if(typeof config.hide_loading_shim == "function")
            config.hide_loading_shim(extra)
        }

        // error callback handler
        var _error = function(a,b,c) {

          // call the custom error callback if
          // it is set
          if(error)
            error(a,b,c)

          // hide the loading shim if it is
          // set
          if(typeof config.hide_loading_shim == "function")
            config.hide_loading_shim(extra)
        }

        if(config.action == "delete") {
          this[config.action](config.path(extra), _success, _error, config.render_errors_to);
        } else {
          this[config.action](config.path(extra), config.data(extra), _success, _error, config.render_errors_to);
        }
      }.bind(this);
      return send_request;
    },

    "profile" : function(path) {
      var t1 = new Date().getTime();
      $.ajax({
        url : this.base_url+"/"+path,
        method : "GET",
        success : function(data) {
          var t2 = new Date().getTime();
          console.log("Request returned", (t2-t1)/1000, data.profiling.queries+" queries");
        }
      }).fail(this.error_handler());
    }
  }
);

/**
 * Base peerctl application class
 * @class Application
 * @namespace Peerctl
 */

Peerctl.Application = tc.cls.define(
  "Application",
  {
    "Application" : function() {
      this.api = new Peerctl.API("/api");
      this.components = {};
      this.init_elements();
    },

    /**
     * Finds and stores all elements that have a data-peerctl
     * attribute set
     *
     * @method init_elements
     */

    "init_elements" : function() {
      var elements = {};
      $("[data-peerctl]").each(function(idx) {
        var id = $(this).data("peerctl");
        elements[id] = $(this);
      });
      this.elements = elements;
    },

    /**
     * Creates a new section in the nav menu
     *
     * @method navmenu_section
     * @param {String} name
     * @returns {jQuery} section header element
     */

    "navmenu_section": function(name) {
      var section_div = this.elements.nav_menu.find('[data-peerctl="nav_menu_'+name+'"]');
      if(section_div.length)
        return section_div;
      var logout_div = this.elements.nav_menu.find("li.divider").last();
      var new_div = $('<li class="dropdown-header">').text(name);
      new_div.attr("data-peerctl", "nav_menu_"+name);
      new_div.insertBefore(logout_div);
      return new_div;
    },

    /**
     * Adds an item into a navmenu section
     *
     * @method navmenu_add
     * @param {String} section_name
     * @param {String} label: item label
     * @param {Function} callback: on click
     * @param {String} glyphicon: glyphicon name
     */

    "navmenu_add": function(section_name, label, callback, glyphicon) {
      if(typeof label == "string")
        label = $('<span>').text(label);

      if(glyphicon) {
        $('<span> </span>').prependTo(label);
        $('<span>').addClass("glyphicon glyphicon-"+glyphicon).
        prependTo(label);
      }

      $('<li>').
        append($('<a>').
        append(label)).
        insertAfter(this.navmenu_section(section_name)).
        click(callback);
    },

    "to_background" : function(component) {
      component.element.appendTo(this.elements.component_idle);
      return this;
    },

    "deactivate_all" : function() {
      var i;
      for(i in this.components) {
        this.components[i].deactivate();
      }
      return this;
    },

    "to_foreground" : function(component) {
      component.element.appendTo(this.elements.component_active);
      return this;
    }

  }
);

/**
 * Base class for API widgets, should be extended.
 *
 * @class APIWidget
 * @namespace Peerctl.Application
 * @constructor
 * @param {Peerctl.Application.API} api
 * @param {String|Function} path: api path without the base path, if
 *    passed as `Function` the function will take these arguments:
 *
 *    - element: the widget element
 *
 *    The function should return the path as a string
 */

Peerctl.Application.APIWidget = twentyc.cls.define(

  "APIWidget",
  {
    "APIWidget" : function(api, path, opt) {
      this.api = api;
      this.opt = opt || {};
      this._path = path;
    },

    /**
     * Returns the api path
     *
     * @param {Object} element: the widget element
     */

    "path" : function(element) {
      if(typeof(this._path) == "function")
        return this._path(element)
      return this._path
    },

    /**
     * bind this widget to an element
     *
     * This function does nothing in the base class and you should
     * override it in the extension
     *
     * What this function accepts is arbitrary, but it should result
     * in a DOM element being initialized for further use by the widget.
     *
     * A widget instance should be able to be bound to
     * multiple elements.
     *
     * @method bind
     */

    "bind" : function(element) {
      return this;
    },

    "copy_events" : function(other, event_types) {
      var i, idx, et, events = $(other).data("events")
      for(i = 0; i < event_types.length; i++) {
        et = event_types[i];
        for(idx in events[et]) {
          $(this).on(et, events[et][idx].handler);
        }
      }
    },

    "show_loading_shim": function(element) {
      if(!element && this.element)
        element = this.element;
      var loading_shim = element.siblings(".loading-shim")
      if(!loading_shim.length) {
        loading_shim = $('<div>').
          addClass("loading-shim").
          insertAfter(element).
          append(
            $('<div>').
            html(this.opt.loading_text || "").
            prepend(
              $("<img>").
              prop("src", Peerctl.STATIC_URL+"loading.gif")
            )
          ).hide();
      }
      loading_shim.show();
      return this;
    },

    "hide_loading_shim": function(element) {
      if(!element && this.element)
        element = this.element;
      element.siblings(".loading-shim").hide()
    },

    "response_handler" : function(element, callback) {
      return function(a,b,c) {
        this.hide_loading_shim(element);
        if(callback)
          callback(a,b,c)
      }.bind(this);
    }

  }
)

/**
 * API widget that allows to associate a form with
 * an api endpoint and action
 *
 * @class APIForm
 * @extends Peerctl.Application.APIWidget
 * @namespace Peerctl.Application
 * @constructor
 */

Peerctl.Application.APIForm = twentyc.cls.extend(
  "APIForm",
  {
    "APIForm" : function(api, path, opt) {
      this.APIWidget(api, path, opt);
    },

    /**
     * Creates an error handler for API responses
     *
     * The callback function accepts these arguments:
     *
     *     - response: request response object
     *     - errors: array of errors
     *     - data: array of data
     *
     * @method error_handler
     * @param {Object} form: form element
     * @param {Function} callback
     */

    "error_handler" : function(form, callback) {
      return function(response, errors, data) {
        this.hide_loading_shim(form);
        if(callback)
          callback(response, errors, data);
        $(errors).each(function() {
          var par = form.find('[name="'+this.name+'"]').parents('.form-group');
          par.addClass('has-error has-feedback');
          $('<span class="help-block validation-error">').text(this.value).appendTo(par)
          $('<span class="glyphicon glyphicon-remove validation-error form-control-feedback">').appendTo(par)

          if(this.name == "non_field_errors" || this.name == "detail") {
            var i, misc = $('<p class="bg-danger validation-error">');
            var nfe_container = form.find(".non-field-errors")
            for(i in this.value) {
              $('<p>').appendTo(misc).append(
                Peerctl.errmsg_node(this.value[i])
              );
            }
            if(nfe_container.length)
              nfe_container.append(misc)
            else
              form.prepend(misc)
          }
        });
      }.bind(this)
    },

    /**
     * Binds a form to this widget making it execute
     * agaisnt the api path and action specified.
     *
     * @method bind
     * @param {jQuery} form
     * @param {String} action: api action
     *
     *     - create
     *     - update
     *     - retrieve
     *     - list
     *     - destroy
     *
     * @param {Function} callback: success callback
     *
     *     Aruments:
     *
     *     - data: data returned by the api at the "data" key
     *     - data_full: full data returned by the api
     *
     * @param {Function} error: error callback
     *
     *     Arguments:
     *
     *     - response: request response object
     *     - errors: array of errors
     *     - data: array of data
     *
     * @param {jQuery} button: if set action will be bound to click on
     *  this button
     *
     * @returns self
     */

    "bind" : function(form, action, callback, error, button) {
      if(!button)
        var button = form.find('[role="api-submit"]')
      button.click(function() {
        var data ={}
        this.show_loading_shim(form);
        form.find('.validation-error').detach();
        form.find('.form-group').removeClass('has-error', 'has-feedback');
        $(form.serializeArray()).each(function() {
          var input = form.find('[name="'+this.name+'"]')
          if(input.prop("type") == "checkbox") {
            data[this.name] = true;
          } else
            data[this.name] = this.value;
        });
        form.find('input[type="checkbox"]').not(":checked").each(function() {
          data[$(this).prop("name")] = false;
        });

        this.api[action](
          this.path(form),
          data,
          this.response_handler(form, callback),
          this.error_handler(form, error)
        );
      }.bind(this));
      return this;
    },

    /**
     * Fill the fields of the form from an api object
     * instance (a single object from the api data)
     *
     * @method fill
     * @param {jQuery} form
     * @param {Object} api_object
     * @returns self
     */

    "fill" : function(form, api_object, meta) {
      form.find('[name]').each(function() {
        var input = $(this),
            name = $(this).attr("name"),
            tag = $(this).prop("tagName").toLowerCase();

        var value = api_object[name], field = (meta && meta.fields ? meta.fields[name] : {});

        if($.inArray(tag, ["input", "textarea"])>-1) {
          if($(this).prop("type") == "checkbox") {
            $(this).prop("checked", value);
          } else {
            $(this).val(value || "");
          }
        } else if($.inArray(tag, ["span", "div", "p"])>-1) {
          $(this).text(value || "");
        } else if($.inArray(tag, ["select"])>-1) {
          input.empty();
          $(field.choices).each(function() {
            $('<option>').
              attr("value", this.value).
              text(this.display_name).
              appendTo(input);
          });
          input.val(value);
        }
      });
      return this;
    }
  },
  Peerctl.Application.APIWidget
);

/**
 * Wires a single input field that will send
 * a value to an api end point
 *
 * @class APIInput
 * @namespace Peerctl.Application
 * @extends APIWidget
 * @constructor
 * @param {Peerctl.API} api
 * @param {Function} path - function that should return api endpoint path
 * @param {Object} opt - object literal for configuration parameters
 */

Peerctl.Application.APIInput = twentyc.cls.extend(
  "APIInput",
  {
    "APIInput" : function(api, path, opt) {
      this.APIWidget(api, path, opt);
      this.param = this.opt.param || {};
      this.opt.loading_text = "";
      this.payload_handler = function(payload) { return payload };
      this.value = 0;
    },

    /**
     * bind to input field
     *
     * @method bind
     * @param {jQuery} input
     * @param {Function} onupdate
     */
    "bind" : function(input, onupdate) {
      var widget = this;
      this.element = input;
      this.element.on("send", function() {
        var payload = widget.payload_handler({"value": $(this).val() });
        var callback = widget.path().put
        if(typeof callback == "function") {
          callback(payload);
        } else if(callback) {
          widget.submit(input, callback, payload, onupdate);
        }
      });

      input.on("focus", function() {
        $(this).siblings("span.error").detach();
        widget.hide_indicator($(this))
      });

      input.on("blur", function() {
        $(this).siblings("span.error").detach();
      });

      input.on("keyup", function(ev) {
        if(ev.keyCode == 13) {
          $(this).trigger("send");
        }
      });

      return this;
    },

    "submit" : function(input, callback, payload, onupdate) {
      this.show_loading_shim();

      input.siblings("span.error").detach()

      var success = function(data) {
        this.hide_loading_shim();
        input.blur();
        this.show_indicator(input, "ok");
        if(onupdate)
          onupdate(data);
      }.bind(this);

      var error = function(response, errors, data) {
        this.hide_loading_shim();
        var errornode = $('<span>').addClass("error")
        $(errors).each(function() {
          errornode.append($('<p>').text(this.value[0]));
        });
        errornode.insertAfter(input);
      }.bind(this);

      this.api.update(callback, payload, success, error);
      return this;
    },

    "payload" : function(handler) {
      this.payload_handler = handler;
      return this;
    },

    /**
     * show an indicator for the api input
     * This could be used to - for example - indicate that the
     * submission has completed successfully
     *
     * @method show_indicator
     * @param {jQuery} input
     * @param {string|jQuery} content content of hte indicator
     *
     *     if a string is passed it will be treaded as a glyphicon
     *     id and the matching glyphicon will be rendered as the contet
     *
     * @param {Number} time if specified the indicator will be removed
     *                 after n ms
     */
    "show_indicator" : function(input, content, time) {
      var css = "";

      this.hide_indicator(input);

      if(typeof content == "string") {
        css = content;
        content = $('<span>').addClass("icon").append(
          $('<img>').attr("src", Peerctl.STATIC_URL+"/md-"+content+".svg")
        );
      }

      var indicator = $('<div>').
        addClass("api-input-indicator "+css).
        append(content).
        insertAfter(input)

      if(time) {
        setTimeout(function() { indicator.detach(); }, time);
      }

      return indicator;
    },

    /**
     * Hide the indicator for the specified input
     *
     * @method hide_indicator
     * @param {jQuery} input
     */

    "hide_indicator" : function(input) {
      input.next(".api-input-indicator").hide()
    }
  },
  Peerctl.Application.APIWidget
);


/**
 * A select input that is wired to an api endpoint
 *
 * @class APISelect
 * @extends APIInput
 * @namespace Peerctl.Application
 * @constructor
 */

Peerctl.Application.APISelect = twentyc.cls.extend(
  "APISelect",
  {
    "APISelect" : function(api, path, opt) {
      this.APIWidget(api, path, opt);
      this.param = this.opt.param || {};
      this.id_field = this.opt.id_field || "id";
      this.name_field = this.opt.name_field || "name";
      this.prepend = this.opt.prepend || [];
      this.process = this.opt.prcess || function(){};
      this.payload_handler = function(payload) { return payload };
      this.value = 0;
    },

    /**
     * Bind to select input
     *
     * @method bind
     * @param {jQuery} select
     * @param {function} onupdate
     */

    "bind" : function(select, onupdate) {
      var widget = this;
      this.element = select;
      this.element.on("mousedown", function() { widget.hide_indicator($(this)) });
      this.element.on("change", function() {
        var payload = widget.payload_handler({"value": $(this).val() });
        console.log("PAYLOAD", payload)
        var callback = widget.path().put
        if(typeof callback == "function") {
          callback(payload);
        } else if(callback) {
          widget.submit(select, callback, payload, onupdate);
        }
      });
      return this;
    },

    /**
     * Refresh options from api
     *
     * @method refresh
     * @param {Mixed} value if specified will select the option
     *                      with the matching value
     *
     * @returns {APISelect} self
     */

    "refresh" : function(value, data) {
      if(typeof value != "undefined") {
        this.value = value;
      }
      if(data) {
        this.fill(data);
        return this;
      }
      this.api.list(this.path().get, this.param, function(data) {
        this.fill(data)
      }.bind(this));
      return this;
    },

    /**
     * Fill the select with options generated from data
     *
     * @method fill
     * @param {Array} data
     *
     *     Should be an array of object literals. Each object
     *     should contain a name and value field. The key names for
     *     these fields can be controlled via the `name_field`
     *     and `id_field` properties of the APISelect widget
     *
     *     If the `prepend` property is set on the APISelect widget
     *     These options will be prepended to the data before generating
     *
     */

    "fill" : function(data) {
      var widget = this;
      widget.element.empty();

      if(!data || !data.length)
        return;

      if(this.prepend && this.prepend.length && this.prepend[0].id != data[0].id) {
        for(i = this.prepend.length-1; i >= 0; i--) {
          data.unshift(this.prepend[i]);
        }
      }

      $(data).each(function() {
        widget.process(this);
        $('<option>').
          val(this[widget.id_field]).
          text(this[widget.name_field]).
          attr('selected', widget.value == this[widget.id_field]).
          appendTo(widget.element)
      });
    }
  },
  Peerctl.Application.APIInput
);


Peerctl.Application.PolicySelect = twentyc.cls.extend(
  "PolicySelect",
  {
    "PolicySelect" : function(put_path, api_object, refresh) {
      var application = window.peerctl;
      this.ip_version = 4;
      this.APISelect(
        application.api,
        function() {
          return {
            get: "policy/"+application.selected_network+"/",
            put: put_path(api_object)
          };
        },
        {
          prepend: [
            { "id" : 0, "name" : "Inherit Policy" }
          ]
        }
      )

      this.payload_handler = function(payload) {
        payload.ipv = this.ip_version
        return payload;
      }.bind(this)


      this.bind($('<select>'), function(data) {
        if(refresh)
          refresh(data[0], api_object);
      }.bind(this))
    },

    "set_ip_version" : function(ip_version) {
      this.ip_version = ip_version;
      return this;
    }
  },
  Peerctl.Application.APISelect
);

Peerctl.Application.APIFieldChoiceSelect = twentyc.cls.extend(
  "APIFieldChoiceSelect",
  {
    "APIFieldChoiceSelect" : function(field_name, get_path, put_path, api_object, refresh) {
      var application = window.peerctl;
      this.field_name = field_name;
      this.APISelect(
        application.api,
        function() {
          return {
            get: get_path(api_object),
            put: put_path(api_object)
          };
        },
        {
          "id_field": "value",
          "name_field": "display_name"
        }
      )
      this.bind($('<select>').addClass("enum-select"), function(data) {
        if(refresh)
          refresh(data[0], api_object);
      }.bind(this))
    },

    "refresh" : function(value) {
      if(typeof value != undefined) {
        this.value = value;
      }
      this.api.meta(this.path().get, function(data) {
        this.fill(data.fields[this.field_name].choices);
      }.bind(this));
      return this;
    }
  },
  Peerctl.Application.APISelect
);



/**
 * API Widget that allows to view a list of objects
 * from an API endpoint
 *
 * @class APIList
 * @extends Peerctl.Application.APIWidget
 * @namespace Peerctl.Application
 * @constructor
 */

Peerctl.Application.APIList = twentyc.cls.extend(
  "APIList",
  {
    "APIList" : function(api, path, opt) {
      this.APIWidget(api, path, opt);
      this.sort_timer = new $util.Timeout(function(){},100);
      this.filter_timer = new $util.Timeout(function(){},100);
      this._data_route = function(data) { return data; };
      this.formatters = {};
      this.actions = {};
      this.options = {},
      this.index = {};
    },

    "extend_list" : function(list) {
      var i, callback, extra;
      for(i in list.formatters)
        this.formatter(i, list.formatters[i]);
      for(i in list.actions)
        this.action(i, list.actions[i]);
      /* this needs more work
       *
      for(i in list.options) {
        callback = list.options[i][0]
        extra = list.options[i][2]
        this.option(i, (callback ? callback.bind(this): null), list.options[i][1], (extra?extra.bind(this):null));
      }
      */
      return this;
    },

    /**
     * Binds a table element to the widget
     *
     * @method bind
     * @param {jQuery} container: table element
     * @param {jQuery} item_template: tr element to use for new rows
     * @returns self
     */

    "bind" : function(container, item_template) {
      this.element = this.container = container;
      this.item_template = item_template;
      this.body = container.find(".api-list-body")

      return this;
    },

    /**
     * Remove all rows from the table
     * This is local, and will not delete items from the API
     *
     * @method clear
     */

    "clear" : function() {
      this.index = {};
      this.body.empty();
    },

    /**
     * Re-sort the table by the currently selected sorting
     * choice
     * @method sort
     */

    "sort" : function() {
      this.sort_timer.set(
        function() {
          this.container.sortable("sortInitial");
        }.bind(this), 100
      );
    },

    /**
     * Define an action callback
     *
     * Use this to link buttons in a row to an action
     *
     * @method action
     * @param {String} name: action name (unique)
     * @param {Function|Object} callback
     *
     *      Arguments:
     *
     *      - id {String|Number}: object id
     *      - api_object {Object}: object
     *      - item {Object}: tr element
     *
     * @returns self
     */

    "action" : function(name, callback) {
      this.actions[name] = callback;
      if(typeof callback == "function") {
        this[name] = callback.bind(this);
      } else if(typeof callback == "object") {
        var list = this;
        callback.render_errors_to = this.container.parent();
        if(callback.loading_shim) {
          callback.show_loading_shim = function(extra) {
            this.show_loading_shim(
              typeof(callback.loading_shim) == "function" ?
              callback.loading_shim(extra.item) : null
            );
          }.bind(this);
          callback.hide_loading_shim = function(extra) {
            this.hide_loading_shim(
              typeof(callback.loading_shim) == "function" ?
              callback.loading_shim(extra.item) : null
            );
          }.bind(this);
        }
        this[name] = this.api.deferred_request(callback);
      }
      return this;
    },

    /**
     * Calls the formatter for the specified field on the specified
     * value
     *
     * @method format
     * @param {String} name: field name
     * @param {Object} api_object
     * @returns {String} formatted value
     */

    "format" : function(name, api_object) {
      if(this.formatters[name]) {
        return this.formatters[name](api_object[name], api_object);
      }
      return api_object[name];
    },

    /**
     * Specify a route to read data from the data object (otherwise
     * assumes data is at root level of the .data container in the
     * rest response
     *
     * @method data_route
     * @param {String|Function} route can be a single keyname, or a function
     *
     *     The function will be passed the complete
     *     data object literal and should return whatever data
     *     you want rendered in the list
     *
     * @returns {APIList} self
     *
     */

    "data_route" : function(route) {
      if(typeof route == "function") {
        this._data_route = route;
      } else {
        this._data_route = function(data) { return data[0][route]; }
      }
      return this;
    },

    /**
     * Add a formatter for the specified field
     *
     * @method formatter
     * @param {String} name: field name
     * @param {Function} format
     *
     *     Arguments:
     *
     *     - value
     *     - api_object
     *
     *     Should return:
     *
     *     - string : the formatted value
     *
     * @returns self
     */

    "formatter" : function(name, format) {
      this.formatters[name] = format;
      return this;
    },

    /**
     * Marks a row/item as new, displaying a color transition
     * @method mark_item_new
     * @param {jQuery} item: tr element
     */

    "mark_item_new" : function(item) {
      item.addClass("new")
      setTimeout(function() { this.removeClass("new"); }.bind(item), 2000);
    },

    /**
     * Marks a row/item as updated, displaying a color transition
     * @method mark_item_updated
     * @param {jQuery} item: tr element
     */

    "mark_item_updated" : function(item) {
      item.addClass("updated")
      setTimeout(function() { this.removeClass("updated"); }.bind(item), 2000);
    },

    /**
     * Return the tr element for the object with the specified id
     *
     * @method get
     * @param {String|Number} api_object_id
     * @returns
     *     - jQuery: tr element
     *     - null: if no tr element was found
     */

    "get" : function(api_object_id) {
      return this.index[api_object_id]
    },

    /**
     * Return the api object that is currently stored
     * in this list from it's id
     *
     * @method get_api_object
     * @param {String|Number} api_object_id
     * @returns
     *     - object
     */

    "get_api_object" : function(api_object_id) {
      return this.get(api_object_id).data("api-object")
    },

    /**
     * Display a delete confirmation dialogue and return whether the user
     * accepts or not
     *
     * @method confirm_delete
     * @param {Object} api_object
     * @returns {Bool}
     */

    "confirm_delete": function(api_object) {
      return confirm(
        "Do you really want to delete: "+(api_object.name || "ID:"+api_object.id)
      );
    },

    "prepare_options" : function(item, api_object) {
      var button = item.find('[data-action="options"]');
      if(button.length == 0)
        return;

      var id = "btn-options-"+item.data("peerctl")+"-"+api_object.id;
      var column = button.parent()
      var buttons = $("<div>").addClass("buttons")
      var dropdown = $("<span>").addClass("dropdown").css("position","relative")
        .appendTo(buttons)

      button.appendTo(dropdown)

      var menu = $("<ul>").addClass("dropdown-menu dropdown-menu-right")
        .attr("aria-labeled-by", id).appendTo(dropdown)

      button
        .mousedown(function() {
          $(this).trigger("options-open", [menu, api_object, item])
        }.bind(this))
        .attr("aria-haspopup","true")
        .attr("aria-expanded","false")
        .attr("data-toggle","dropdown")
        .attr("id", id)
        .appendTo(dropdown)

      buttons.appendTo(column)

      $(this).trigger("options-populate", [menu, api_object, item])
    },

    /**
     * Add option to row context menu
     *
     * @method option
     * @param {String} label
     * @param {Function} callback(api_object, item)
     * @param {String} glyphicon bootstrap3 glyphicon name
     */

    "option" : function(label, callback, glyphicon, extra) {
      $(this).on("options-populate", function(e, menu, api_object, item) {
        this._option(menu, api_object, item, label, callback, glyphicon, extra);
      }.bind(this));
      this.options[label] = [callback, glyphicon, extra];
      return this;
    },

    "_option" : function(menu, api_object, item, label, callback, glyphicon, extra) {
        if(callback) {
          var node = $('<li>').appendTo(menu);
          node.append(
            $('<a>').
            append($util.menu_label(label, glyphicon))
          ).click(function() {
            callback(api_object, item, this);
          }.bind(this));
        } else {
          var node = $('<li>').appendTo(menu);
          node.addClass("dropdown-header").text(label);
          var node = $('<li>').appendTo(menu);
        }

        if(extra)
          extra(node, api_object, item, this);

        return node;
    },

    /**
     * Add dynamic options to row context menu
     *
     * These will be regenerated / refreshed everytime the
     * menu is opened
     *
     * @method dynamic_options
     * @param {String} group arbitrary group name for these options
     * @param {Function} fn_fetch
     */

    "dynamic_options" : function(group, fn_fetch) {
      $(this).on("options-open", function(e, menu, api_object, item) {
        menu.find('[data-optgroup="'+group+'"]').detach()
        fn_fetch(function(label, callback, glyphicon) {
          var opt = this._option(menu, api_object, item, label, callback, glyphicon);
          opt.attr("data-optgroup", group);
        }.bind(this), api_object);
      }.bind(this));
      return this;
    },

    "option_complex" : function(label, create, open, glyphicon) {
      this.option(label, null, glyphicon, function(node, api_object, item) {
        var other = create(api_object, item, this);
        other.mousedown(function(e) { e.stopPropagation(); });
        other.click(function(e) { e.stopPropagation(); });
        node.append(other);
      }.bind(this));
      if(open) {
        $(this).on("options-open", function(e, menu, api_object, item) {
          open(this.get_api_object(api_object.id), item, this);
        }.bind(this));
      }
      return this;
    },


    "option_input" : function(label, path, opt, value) {
      var widget_id = "api_input:"+label;
      this.option_complex(
        label,
        function(api_object, item, api_list) {
          var holder = $('<div>').
                        addClass("holder")
          var input = $('<input>').
                        appendTo(holder)

          if(opt.wide)
            input.addClass("input-wide")

          var api_input = new Peerctl.Application.APIInput(
            this.api,
            function() { return {"put": path(api_object, api_list)} },
            opt
          ).bind(input, function(data) {
            this.update_or_add(data[0]);
          }.bind(this));

          item.data(widget_id, input);

          return holder;
        }.bind(this),
        function(api_object, item, api_list) {
          var val = (value ? value(api_object, api_list) : null);
          item.data(widget_id).val(val);
        }
      );
      return this;
    },

    /**
     * Delete action - Deletes the object with the specified id
     *
     * This is local, the object will NOT be deleted from the API, see `delete_remote` instead.
     *
     * @method delete
     * @param {String|Number} api_object_id
     */

    "delete" : function(api_object_id) {
      var item = this.get(api_object_id);
      item.detach();
      delete this.index[api_object_id];
    },


    /**
     * Delete action - Deletes the object with the specified id
     *
     * This is REMOTE and LOCAL - the object will be removed from the server via the API.
     *
     * @method delete
     * @param {Object} payload - sent from list action callback
     *
     *     - id : api_object id (required)
     *     - data : api_object (not needed)
     *     - item : tr element (not needed)
     */

    "delete_remote" : function(payload) {
      var api_object_id = payload.id;
      var item = this.get(api_object_id);
      if(!item || !this.confirm_delete(item.data("api-object")))
        return;
      this.api.delete(this.path("delete")+"/"+api_object_id+"/", function(r) {
        this.delete(api_object_id);
        return true;
      }.bind(this), null, this.container.parent());
    },

    /**
     * Add a row
     *
     * This action is local only, it will not actually add an element via the API
     *
     * @method add
     * @param {Object} api_object
     * @param {Bool} effect: if true mark row as new
     */

    "add" : function(api_object, effect) {
      if(!this.get(api_object.id)) {

        var payload = {cancel:false};
        $(this).trigger("row-add", [api_object, payload])
        if(payload.cancel)
          return;

        var k,
            item = this.item_template.clone(),
            widget = this;

        this.wire_actions(item, api_object)

        for(k in api_object) {
          item.find('[name="'+k+'"]').
            html(this.format(k, api_object)).
            attr("data-sort-value", api_object[k]);
        }
        item.appendTo(this.body);
        this.index[api_object.id] = item;

        $(this).trigger("row-added", [item, api_object])

        this.format_row(api_object);
        if(effect)
          this.mark_item_new(item);
      }
      this.sort()
    },

    "wire_actions" : function(item, api_object) {
      var widget = this;
      item.attr("data-row-id", api_object.id).
        attr("id", "row-"+api_object.id).
        data("api-object", api_object)

      item.find('[data-action]').each(function() {
        var action = $(this).data("action");
        if(action == "options") {
          widget.prepare_options(item, api_object);
          return;
        }
        $(this).click(function(){ this[action]({
          "list" : this,
          "id" : api_object.id,
          "data" : item.data("api-object"),
          "item" : item
        });
        }.bind(widget));
      });

    },

    /**
     * Update a row.
     *
     * This is local only, it will NOT update the object on the server via the API.
     *
     * @method update
     * @param {Object} api_object
     * @param {Bool} effect: if true mark row as updated
     */

    "update" : function(api_object, effect) {
      var k, item = this.get(api_object.id);

      $(this).trigger("row-update", [api_object])
      if(!item)
        return;
      for(k in api_object) {
        item.find('[name="'+k+'"]').first().html(this.format(k, api_object));
      }
      item.data("api-object", api_object)
      this.sort()
      this.format_row(api_object);
      if(effect)
        this.mark_item_updated(item);
    },

    /**
     * Calls updated or add depending on whether the row for the
     * object already exists or not
     *
     * @method update_or_add
     * @param {Object} api_object
     * @param {Bool} effect: if true mark row as new or updated
     * @returns {jQuery}: row element
     */

    "update_or_add" : function(api_object, effect) {
      var item = this.get(api_object.id);
      if(item)
        return this.update(api_object, effect);
      return this.add(api_object, effect);
    },

    "apply_filters" : function() {
      this.filter_timer.set(
        function() {
          this.body.filterable("filter");
        }.bind(this), 100
      );
    },

    /**
     * Load objects from the api into the list
     *
     * @method refresh
     * @param {Function} callback
     *
     *     Arguments:
     *
     *     - data: api response data from "data" key
     */

    "refresh" : function(callback, error) {
      var widget = this;
      var ts = new Date().getTime(), ts_1;
      $(this).trigger("before-refresh")
      this.api.list(this.path("list"), null, function(_data) {
        console.log("Data returned "+(new Date().getTime()-ts)+"ms");
        widget.refresh_data(_data, callback)
        var ts2 = new Date().getTime();
        console.log("Finished after "+(ts2-ts)+" ms");
        $(widget).trigger("after-refresh");
      }, error, this.container.parent());
      return this;
    },

    "refresh_data" : function(_data, callback) {
        this.clear();
        var i, data = this._data_route(_data);

        var promise_refresh = this.promise_refresh();

        promise_refresh.then(function() { new Promise(function(resolve, error) {
          for(i = 0; i < data.length; i++) {
            this.update_or_add(data[i]);
          }
          this.apply_filters();
          if(callback)
            this.sort_timer.ready(function() { callback(data); });
          resolve();
        }.bind(this))}.bind(this));


        return this;
    },

    "refresh_item" : function(id, extra) {
      this.api.retrieve(this.path("retrieve", extra)+"/"+id+"/", {}, function(data) {
        this.update_or_add(data)
      }.bind(this));
    },

    "promise_refresh" : function() {
      return new Promise(function(resolve, error) { resolve(); });
    },

    "promise" : function(event_name, callback) {
      this["promise_"+event_name] = callback;
      return this;
    },

    /**
     * Class the row formatter for the row that renders
     * the specified api object. This is done automatically during
     * update and add.
     *
     * @method format_row
     * @param {Object} api_object
     */

    "format_row" : function(api_object) {
      var item = this.get(api_object.id);
      var formatter = this.formatters["row"]
      if(formatter) {
        formatter(item, api_object);
      }
    },

    "filter" : function(input, filter) {
      return;
    }
  },
  Peerctl.Application.APIWidget
)

/**
 * Base class for application components. You should extend
 * this
 *
 * @class Component
 * @namespace Peerctl.Application
 * @constructor
 * @param {Application} application
 * @param {String} component_name: name of the component (unique)
 *
 *     Note: a html element with the attribue `data-peerctl`
 *     set to this value needs to exist in the
 *     DOM
 */

Peerctl.Application.Component = twentyc.cls.define(
  "Component",
  {
    "Component" : function(application, component_name) {
      this.application = application;

      application.components[component_name] = this;

      this.element = application.elements[component_name];
      this.loading_shim = $('<div>').addClass("loading-shim").
        appendTo(this.element).append($('<div>').html("Loading").prepend($("<img>").prop("src", Peerctl.STATIC_URL+"loading.gif"))).hide();
      this.tag = "component"
    },

    /**
     * Activate component, making it visible to the user in the UI
     *
     * @method activate
     */

    "activate" : function(solo) {
      if(solo)
        this.application.deactivate_all();
      this.application.to_foreground(this);
      if(!this.active) {
        this.active = true;
        $(this).trigger("activated");
      }
    },

    /**
     * Deactivate component, hiding it from the user in the UI
     *
     * @method deactivate
     */

    "deactivate" : function() {
      this.application.to_background(this);
      if(this.active) {
        this.active = false;
        $(this).trigger("deactivated");
      }
    },

    /**
     * Get the tab with the specified id
     *
     * @method tab
     * @param {String} id
     * @returns {jQuery} bootstrap tab
     */

    "tab" : function(id) {
      return this.element.find('.nav-tabs a[data-target="#'+id+'"]');
    },

    /**
     * Get the tab content with the specified id
     *
     * @method tab_content
     * @param {String} id
     * @return {jQuery} bootstrap tab content container
     */

    "tab_content" : function(id) {
      return this.element.find('.tab-content div[id="'+id+'"]');
    },

    /**
     * Return if the tab with the specified id exists
     * @param {String} id
     * @returns {Bool}
     */

    "has_tab" : function(id) {
      return (this.tab(id).length > 0);
    },

    /**
     * Add a new tab
     *
     * @method add_tab
     * @param {String} id: tab id (unique to the component)
     * @param {String} label
     * @param {jQuery} content
     * @param {Bool} focus: if true set focus to the tab
     * @param {Bool} locked: if true tab cannot be closed by middle-mouse click
     *
     * @returns {jQuery} bootstrap tab
     */

    "add_tab" : function(id, label, content, focus, locked) {
      var tab = $('<li role="presentation" class="inactive">');
      tab.append(
          $('<a data-target="#'+id+'" role="tab" aria-controls="'+id+'" data-toggle="tab">').
            html(label).append(
              $('<span>').addClass('tab-close').append(
                $('<span>').addClass("glyphicon glyphicon-remove")
              ).click(function(e) {
                tab.parent().find('li a:first').tab('show');
                this.close_tab(id);
                e.preventDefault();
              }.bind(this))
            )
        ).
        appendTo(this.element.find('.nav-tabs'));

      $('<div class="tab-pane inactive" role="tabpanel" id="'+id+'">').
        append(content).
        appendTo(this.element.find('.tab-content'));

      if(focus)
        tab.find('a').tab("show");

      if(!locked) {
        tab.mouseup(function(e) {
          if(e.button==1) {
            tab.parent().find('li a:first').tab('show');
            this.close_tab(id);
            e.preventDefault();
          }
        }.bind(this));
      }
      return tab.find('a');
    },

    /**
     * Close tab with the specified id
     *
     * @method close_tab
     * @param {String} id
     */

    "close_tab"  : function(id) {
      this.tab(id).parent('li').detach();
      this.tab_content(id).detach();
    },

    /**
     * Returns the tab with the specified id
     *
     * If the tab does not exist, it will be created first.
     *
     * @method get_or_add_tab
     * @param {String} id: tab id (unique to the component)
     * @param {String} label
     * @param {jQuery} content
     * @param {Bool} focus: if true set focus to the tab
     * @param {Bool} locked: if true tab cannot be closed by middle-mouse click
     *
     * @returns {jQuery} bootstrap tab
     */

    "get_or_add_tab" : function(id, label, content, focus, locked) {
      var tab = this.tab(id);
      if(!tab.length) {
        tab = this.add_tab(id, label, content, focus, locked);
      } else {
        this.tab_content(id).empty().append(content);
      }
      if(focus)
        tab.tab('show');
    },

    /**
     * Creates a new section in the nav menu
     *
     * @method menu_section
     * @param {String} name
     * @returns {jQuery} section header element
     */

    "menu_section": function(name) {
      var menu = this.application.elements[this.tag+"_menu"]
      var section_div = menu.find('[data-peerctl="'+this.tag+'_menu_'+name+'"]');
      if(section_div.length)
        return section_div;
      var last_div = menu.find("li.divider").last();
      var new_div = $('<li class="dropdown-header">').text(name);
      new_div.attr("data-peerctl", this.tag+"_menu_"+name);
      if(last_div.length)
        new_div.insertBefore(last_div);
      else
        new_div.appendTo(menu);
      return new_div;
    },


  }
)


/**
 * Peerctl Network Manager Application
 * @class NetworkApplication
 * @namespace Peerctl
 * @extends Peerctl.Application
 */

Peerctl.NetworkApplication = twentyc.cls.extend(
  "NetworkApplication",

  {
    "NetworkApplication" : function() {
      this.Application();
      window.peerctl = this;
      this.networks = {};
      this.navmenu_add("User", "Preferences", function() { this.userpref.show() }.bind(this), "cog");
      this.selected_network = 0;
      this.load_networks();
      this.devices = new Peerctl.NetworkApplication.DeviceComponent(this, "component_net_device");
      this.policies = new Peerctl.NetworkApplication.PolicyComponent(this, "component_net_policy");
      this.ports= new Peerctl.NetworkApplication.PortComponent(this, "component_net_port");
      this.peers= new Peerctl.NetworkApplication.PeerComponent(this, "component_net_peer");
      this.emltmpls = new Peerctl.NetworkApplication.EmailTemplateComponent(this, "component_net_emltmpl");
      this.devicetmpls = new Peerctl.NetworkApplication.DeviceTemplateComponent(this, "component_net_devicetmpl");
      this.make_a_wish = new Peerctl.Modals.MakeAWish(this);
      this.userpref = new Peerctl.Modals.UserPreferences(this);

      this.elements.btn_feature_request.click(function() {
        this.make_a_wish.show();
      }.bind(this));

      this.elements.btn_peering_lists.click(function() {
        this.show_page_peerlist();
      }.bind(this));

      this.elements.btn_templates.click(function() {
        this.show_page_templates();
      }.bind(this));
    },

    /**
     * Show page
     * @method show_page
     * @param {String} page "peerlist" or "templates"
     */

    "show_page" : function(page) {
      if(!this.selected_network)
        return;
      if(page == "templates")
        this.show_page_templates();
      else
        this.show_page_peerlist();
    },

    /**
     * Show the peering list page
     * @method show_page_peerlist
     */

    "show_page_peerlist" : function() {
        this.components.component_net_peer.activate(true);
        this.elements.header_menu.find(".menu-tab").removeClass("active");
        this.elements.btn_peering_lists.addClass("active");
        this.page = "peerlist";
        document.location.href = "#"+this.selected_network+"-"+this.page;
    },

    /**
     * Show the templates page
     * @method show_page_templates
     */

    "show_page_templates" : function() {
        this.components.component_net_policy.activate(true);
        this.components.component_net_emltmpl.activate(false);
        this.components.component_net_devicetmpl.activate(false);
        this.elements.header_menu.find(".menu-tab").removeClass("active");
        this.elements.btn_templates.addClass("active");
        this.page = "templates";
        document.location.href = "#"+this.selected_network+"-"+this.page;
    },

    /**
     * Selects the network which is to be managed
     *
     * Will reload the UI elements with the network's data and sub windows
     *
     * @method select_network
     * @param {Number} asn
     */
    "select_network": function(asn, data) {
      this.elements.selected_target.find('.name').text(this.networks[asn].name);
      this.elements.selected_target.find('.sub').text(" - "+asn);
      this.selected_network = asn;
      this.selected_network_data = data;
      this.devices.refresh();
      this.policies.refresh();
      this.ports.refresh();
      this.emltmpls.refresh();
      this.devicetmpls.refresh();
      document.location.href = "#"+asn+"-"+this.page;
      $(this).trigger('network_change', [asn]);
      $('#selected-asn').text("AS"+asn);
    },

    /**
     * Loads all networks the managing user has write permissions
     * to.
     *
     * Also adds them to the nav menu
     * @method load_networks
     */
    "load_networks" : function() {
      var instance = this;
      var preferred_network = $util.url_anchor_asn();
      var page = $util.url_anchor_page();
      this.api.list("/net", null, function(data) {
        $(Peerctl.util.sort(data, "name", true)).each(function() {
          instance.navmenu_add("Networks", this.name || (this.asn + " (Network Data Missing)"), function() { instance.select_network(this.asn, this) }.bind(this));
          instance.networks[this.asn] = this;
          if(!instance.selected_network) {
            if(!preferred_network || preferred_network == this.asn) {
              instance.select_network(this.asn, this);
              instance.show_page(page);
            }
          }
        });
      });
    }
  },
  Peerctl.Application
);

/**
 * `Devices` component in the network application
 *
 * Allows you to manage a network's devices
 *
 * @class DeviceComponent
 * @extends Peerctl.Application.Component
 * @namspace Peerctl.NetworkApplication
 * @construtor
 */

Peerctl.NetworkApplication.DeviceComponent = twentyc.cls.extend(
  "DeviceComponent",
  {

    "DeviceComponent" : function(application, component_name) {
      this.Component(application, component_name);

      this.tag = "device"

      application.api.meta("device/0/", function(meta) {
        this.api_specs = meta;
        this.api_form_create.fill(
          application.elements.form_net_device_add,
          {
            type: meta.fields.type.choices[0].value
          },
          meta
        )
      }.bind(this));

      /**
       * Use APIList widget to display the list of devices
       */
      this.api_list = new Peerctl.Application.APIList(
        application.api,
        function(){ return "device/"+application.selected_network+"/" }
      ).bind(
        application.elements.list_net_device,
        application.elements.list_net_device_item
      ).formatter("type", function(value, api_object)
        {
          return $util.choice_label(this.api_specs.fields.type.choices, value);
        }.bind(this)
      ).formatter("name", $fmt.device_name
      ).option(
        "Edit",
        function(device, item) {
        /*
         * edit action
         *
         * When a user clicks the edit button this action
         * will be called.
         */

        var device_id = device.id;

        // create new html form to use
        var container = application.elements.container_net_device_edit.
          clone();

        var form = container.find('.device-form').
          data("device-id", device_id);

        // add port management list
        port_api_list = new Peerctl.Application.APIList(
          application.api,
          "port/"+application.selected_network+"/"+device_id+"/"
        ).bind(
          application.elements.list_device_port.clone().appendTo(container.find('.ports')),
          application.elements.list_device_port_item
        ).formatter(
          "speed", $fmt.speed
        ).refresh();

        // bind APIForm instance to new html form and fill
        // html form with current api object data
        this.api_form_edit.bind(
          form,
          "update",
          function(data) {
            // on successful update, update the row in the list
            this.api_list.update(data[0], true);
            // focus the list tab
            this.tab('device-list').tab('show');
            // close the edit tab
            this.close_tab("device-"+device_id);
          }.bind(this)
        ).fill(form, item.data("api-object"), this.api_specs);

        // add tab for the device and focus it
        this.get_or_add_tab("device-"+device_id, device.name, container, true);
        }.bind(this),
        "pencil"
      ).dynamic_options(
        "configure", function(optionize, api_object) {
          application.api.list(
            "devicetmpl/"+application.selected_network+"/list_available/",
            {device_type:api_object.type},
            function(data) {
              $(data).each(function() {
                optionize("Configure "+this.name, function(api_object) {
                  new Peerctl.Modals.DeviceTemplate(
                    application, api_object, this.type).show();
                }.bind(this), "list-alt");
              });
            }
          )
        }.bind(this)
      );

      /**
       * Use APIForm widget to bind the html form for device
       * creation to the API
       */
      this.api_form_create = new Peerctl.Application.APIForm(
        application.api,
        function(){ return "device/"+application.selected_network+"/" }
      ).bind(
        application.elements.form_net_device_add,
        "create",
        function(data) {
          // on successful creation add item to list
          this.api_list.add(data[0], true);
          // focus list tab
          this.element.find('[aria-controls="device-list"]').tab("show");
        }.bind(this)
      )


      /**
       * APIForm widget we will use for editing existing devices
       * (see above)
       */
      this.api_form_edit = new Peerctl.Application.APIForm(
        application.api,
        function(form){ return "device/"+application.selected_network+"/"+form.data("device-id")+"/" }
      );


    },

    /**
     * Refresh the device list from the api
     *
     * @method refresh
     */

    "refresh" : function() {
      this.api_list.refresh(function(data) {
        // if device list is empty, focus the 'add device'
        // tab automatically
        if(!data.length) {
          this.tab('device-add').tab('show');
        }
      }.bind(this));
    }
  },
  Peerctl.Application.Component
);

/**
 * `Policies` component in the network application
 *
 * Allows you to manage a network's policies
 *
 * @class PolicyComponent
 * @extends Peerctl.Application.Component
 * @namspace Peerctl.NetworkApplication
 * @construtor
 */

Peerctl.NetworkApplication.PolicyComponent = twentyc.cls.extend(
  "PolicyComponent",
  {

    "PolicyComponent" : function(application, component_name) {
      this.Component(application, component_name);

      this.application  = application;

      this.tag = "policy"
      this.container_policy_add = this.element.find("#policy-add")
      this.container_policy_edit = this.element.find("#policy-edit")

      application.api.meta("policy/0/", function(meta) {}.bind(this));

      /**
       * Use APIList widget to display the list of policys
       */
      this.api_list = new Peerctl.Application.APIList(
        application.api,
        function(){ return "policy/"+application.selected_network+"/" }
      ).bind(
        application.elements.list_net_policy,
        application.elements.list_net_policy_item
      ).formatter("row", function(row, api_object) {
        var global = row.find(".global");
        if(!api_object.is_global4 && !api_object.is_global6)
          global.hide()
        else
          global.show()

        if(api_object.is_global4)
          global.find(".ipv4").show()
        else
          global.find(".ipv4").hide()

        if(api_object.is_global6)
          global.find(".ipv6").show()
        else
          global.find(".ipv6").hide()

      }).action("edit", function(payload) {
        /*
         * edit action
         *
         * When a user clicks the edit button this action
         * will be called.
         */

          this.show_edit_policy(payload.data, payload.item);

        }.bind(this)
      );

      // FIXME:
      // delete policy needs to refresh dropdowns in peerlist


      /**
       * Use APIForm widget to bind the html form for policy
       * creation to the API
       */
      this.api_form_create = new Peerctl.Application.APIForm(
        application.api,
        function(){ return "policy/"+application.selected_network+"/" }
      ).bind(
        application.elements.form_net_policy_add,
        "create",
        function(data) {
          // on successful creation add item to list
          this.api_list.add(data[0], true);
          this.api_list.refresh();
          application.peers.refresh();
        }.bind(this)
      )


      /**
       * APIForm widget we will use for editing existing policys
       * (see above)
       */
      this.api_form_edit = new Peerctl.Application.APIForm(
        application.api,
        function(form){ return "policy/"+application.selected_network+"/"+form.data("policy-id")+"/" }
      );


    },

    /**
     * Refresh the policy list from the api
     *
     * @method refresh
     */

    "refresh" : function() {
      this.api_list.refresh(function(data) {
        // if policy list is empty, focus the 'add policy'
        // tab automatically
        if(!data.length) {
          this.tab('policy-add').tab('show');
        }
      }.bind(this));
    },

    "show_edit_policy" : function(policy, item) {
      // create new html form to use
      var container = this.application.elements.container_net_policy_edit.
        clone();
      var application = this.application, policy_id = policy.id;

      var form = container.find('.policy-form').
        data("policy-id", policy_id);

      form.find(".cancel").click(function() {
        this.show_create_policy();
      }.bind(this));

      // bind APIForm instance to new html form and fill
      // html form with current api object data
      this.api_form_edit.bind(
        form,
        "update",
        function(data) {
          // on successful update, update the row in the list
          this.api_list.update(data[0], true);
          // focus the list tab
          this.tab('policy-list').tab('show');
          // close the edit tab
          this.close_tab("policy-"+policy_id);
          this.api_list.refresh();
          application.ports.refresh();
          application.peers.refresh();
          this.show_create_policy();
        }.bind(this)
      ).fill(form, item.data("api-object"), this.api_specs);

      this.container_policy_add.hide()
      this.container_policy_edit.empty().append(form).show();
    },

    "show_create_policy" : function() {
      this.container_policy_add.show()
      this.container_policy_edit.empty().hide();
    }
  },
  Peerctl.Application.Component
);


/**
 * `Ports` component in the network application
 *
 * Allows you to manage a network's ports
 *
 * @class PortComponent
 * @extends Peerctl.Application.Component
 * @namspace Peerctl.NetworkApplication
 * @construtor
 */

Peerctl.NetworkApplication.PortComponent = twentyc.cls.extend(
  "PortComponent",
  {

    "PortComponent" : function(application, component_name) {
      this.Component(application, component_name);

      this.tag = "port"

      application.api.meta("port/0/", function(meta) {
        this.api_specs = meta;
      }.bind(this));

      /**
       * Use APIList widget to display the list of devices
       */
      this.api_list = new Peerctl.Application.APIList(
        application.api,
        function(){ return "port/"+application.selected_network+"/" }
      ).bind(
        application.elements.list_net_port,
        application.elements.list_net_port_item
      ).formatter(
        "speed", $fmt.speed
      ).formatter(
        "policy", $fmt.policy
      )
    },


    /**
     * Refresh the port list from the api
     *
     * @method refresh
     */

    "refresh" : function() {
      this.api_list.refresh(function(data) {
      }.bind(this));
    }
  },
  Peerctl.Application.Component
);

/**
 * `Peers` component in the network application
 *
 * Allows you to manage a network's peers
 *
 * @class PeerComponent
 * @extends Peerctl.Application.Component
 * @namspace Peerctl.NetworkApplication
 * @construtor
 */

Peerctl.NetworkApplication.PeerComponent = twentyc.cls.extend(
  "PeerComponent",
  {

    "PeerComponent" : function(application, component_name) {
      var component = this;

      this.Component(application, component_name);

      this.tag = "peer"
      this.selected_port = 0;
      this.input_select_port = this.element.find('#select-port')
      this.container_device_info = this.element.find('#device-info')
      this.btn_device_config = this.container_device_info.find("#btn-device-config")
      this.btn_email_peers = this.element.find("#btn-email-peers")

      this.btn_device_config.click(function() {
         new Peerctl.Modals.DeviceTemplate(
             application, this.api_object.device, this.device_template()).show();
      }.bind(this));

      this.btn_email_peers.click(function() {
        var modal = new Peerctl.Modals.BulkEmail(application, this.ports[this.selected_port].ix).show();
      }.bind(this));

      this.input_select_port.on("change", function() {
        component.select_port($(this).val(), true);
      });

      this.element.find(".ixcfg").mobileCollapse();

      $(application).on("network_change", function(e, asn) {
        this.selected_port = 0;
        this.loading_shim.show();
        this.refresh_port_select(asn);
     }.bind(this));

      application.api.meta("peer/0/0/", function(meta) {
        this.api_specs = meta;
      }.bind(this));

      /**
       * Use APIList widget to display the list of devices
       */
      this.api_list = new Peerctl.Application.APIList(
        application.api,
        function(){
          return "peer/"+application.selected_network+"/"+
                 this.selected_port;
        }.bind(this)
      ).bind(
        application.elements.list_net_peer,
        application.elements.list_net_peer_item

      ).promise(
        "refresh",
        function() {
          return new Promise(
            function(resolve, error) {
              application.api.list(
                "policy/"+application.selected_network+"/",
                {},
                function(data) {
                  this.api_list.policies = data;
                  resolve();
                }.bind(this),
                function(result) {
                  error(["Couldnt load policies", result])
                }
              );
            }.bind(this)
          )
        }.bind(this)
      ).formatter(
        "peerses_status", function(value, api_object) {
          if(value == "ok")
            return "live"
          else if(value == "" || !value)
            return "-"
          else
            return value
        }
      ).action(
        "set_md5",
        function(item) {
          var modal = new Peerctl.Modals.MD5Password(
            this.application, item.data, function(peer){
              this.api_list.update_or_add(peer);
            }.bind(this))
          modal.show();
        }.bind(this)
      ).action(
        "email_peer",
        function(item) {
          var modal = new Peerctl.Modals.PeersesEmailWorkflow(this.application, item.data, this.selected_port, this.api_list);
          modal.show();
        }.bind(this)
      ).action(
        "add_peerses",
        {
          "loading_shim" : function(item) { return item },
          "path" : function(extra) {
            return "peerses/"+this.application.selected_network+
                   "/"+extra.data.port_id+"/";
          }.bind(this),
          "action" : "create",
          "data" : function(peer) {
            return { member : peer.id, through : peer.data.origin_id }
          },
          "success" : function(data, all_data, sent_data) {
            this.list.update_or_add(data[0])
          }
        }
      ).action(
        "delete_peerses",
        {
          "loading_shim" : function(item) { return item },
          "path" : function(extra) {
            var otherpeer = extra.data;
            return "peerses/"+this.application.selected_network+
                   "/"+otherpeer.port_id+"/"+(otherpeer.peerses);
          }.bind(this),
          "action" : "delete",
          "confirm" : "Are you sure you want to remove this live session?",
          "success" : function(data, all_data, sent_data, extra) {
            this.list.refresh_item(extra.data.origin_id);
          }
        }


      ).action(
        "peer_details",
        function(item) {

          var mutual_locs_container = item.item.find("#mutual-locs-container")

          if(!mutual_locs_container.is(":empty")) {
            mutual_locs_container.empty();
            item.item.find(".expandable").removeClass("expanded").addClass("collapsed")
            item.item.data("mutual_locs", null)
            return;
          }


          var container = application.elements["container_net_"+this.tag+"_details"].clone();
          var api_object = item.data;
          var mutual_locs = this.mutual_locs_list(api_object,
            function() {
              item.item.find(".expandable").removeClass("collapsed").addClass("loading")
            },
            function() {
              item.item.find(".expandable").removeClass("loading").addClass("expanded")
            }
          );
          container.find('#mutual-loc').append(mutual_locs.container);
          mutual_locs_container.append(container)

          item.item.data("mutual_locs", mutual_locs)

        }.bind(this)
      ).formatter(
        "row", function(row, api_object) {
          if(!api_object.ipaddr6)
            row.find(".ipaddr6-toggle").hide();
          if(!api_object.ipaddr4)
            row.find(".ipaddr4-toggle").hide();

          row.find(".pdb-link").attr("href", "https://as"+api_object.asn+".peeringdb.com");

          row.find(".filters").attr("data-filter-value-peerses", api_object.peerses);
          row.find(".filters").attr("data-filter-value-onrs", api_object.is_rs_peer?1:0);

          if(api_object.is_rs_peer) {
            row.addClass("is-rs")
          } else {
            row.removeClass("is-rs")
          }


          this.format_row_prefixes(row, api_object, 4);
          this.format_row_prefixes(row, api_object, 6);

          this.format_row_ipaddr(row, api_object);

          var btn_expand = row.find('.btn-expand')
          var btn_show_config = row.find('.btn-show-peer-config')


          btn_show_config.click(function() {
            console.log("showing peer config", api_object);
             new Peerctl.Modals.DeviceTemplate(
               application, this.api_object.device, this.device_template(), api_object).show();
          }.bind(this));


          // we do not want to wire the button to
          // expand mutual locations more than once, so
          // bail if it's already wired.
          if(row.data("wired"))
            return;
          row.data("wired",true);

          btn_expand.click(function() {
            this.api_list.peer_details({
              "list" : this.api_list,
              "data" : api_object,
              "id" : api_object.id,
              "item" : this.api_list.get(api_object.id)
            });
          }.bind(this));
        }.bind(this)
      ).formatter(
        "policy_ratio", function(value, api_object) {
          return (value ? "Required" : "Not required")
        }
      )

      $(this.api_list).on("before-refresh", function() {
        this.asn_index = {};
      });

      $(this.api_list).on("row-added", function(e, row, peer) {
        if(!this.asn_index)
          this.asn_index = {}
        if(!this.asn_index[peer.asn])
          this.asn_index[peer.asn] = row
        row.mobileCollapse()
        row.mobileCollapse("collapse");
      });

      $(this.api_list).on("row-add", function(e, peer, payload) {
        if(this.asn_index && this.asn_index[peer.asn])
          payload.cancel = true;
      });

    },

    "format_row_ipaddr" : function(row, peer) {
      var _row, i, ipaddr, peerses_list = row.find(".peerses-list")
      peerses_list.empty();
      var peerses_ok = false;
      peer.ipaddr.sort(function(a,b) { return b.peerses - a.peerses });

      for(i = 0; i < peer.ipaddr.length; i++) {
        ipaddr = peer.ipaddr[i];
        _row = this.application.elements.list_net_peer_ipaddr.clone();
        _row.find(".ipaddr4").text(ipaddr.ipaddr4)
        _row.find(".ipaddr6").text(ipaddr.ipaddr6)
        _row.find(".ix_name").text(peer.ix_name)
        this.format_row_policy(_row, ipaddr, 4);
        this.format_row_policy(_row, ipaddr, 6);

        if(ipaddr.peerses_status=="ok") {
          peerses_ok = true;
          _row.removeClass("bg-normal").addClass("bg-success")
          _row.find(".uneditable").removeClass("uneditable").addClass("editable")
        } else {
          _row.find(".editable").removeClass("editable").addClass("uneditable")
          _row.removeClass("bg-success").addClass("bg-normal")
        }

        ipaddr.port_id = peer.port_id

        this.api_list.wire_actions(_row, ipaddr);

        peerses_list.append(_row);

      }
      if(peerses_ok) {
        row.find("#btn-show-peer-config").show()
        row.addClass("bg-success").removeClass("bg-normal");
        if(peer.md5 && peer.md5 != "")
          row.addClass("md5-set")
        else
          row.removeClass("md5-set")

      } else {
        row.find("#btn-show-peer-config").hide()
        row.removeClass("bg-success").addClass("bg-normal");
      }
    },


    "format_row_policy" : function(row, peer, version, callback) {
      var field_name = "policy"+version;
      var policy = peer[field_name];
      if(policy) {
        row.find("."+field_name+".holder").first().empty().append(
          new Peerctl.Application.PolicySelect(
            function(peer) {
              return "peerses/"+this.application.selected_network+
                     "/"+peer.port_id+
                     "/"+peer.peerses+
                     "/set_policy/";
            }.bind(this),
            peer,
            callback
          ).set_ip_version(version).
            refresh(
              policy.inherited ? 0 : policy.id,
              this.api_list.policies
            ).element
        );
      }
    },

    "format_row_prefixes" : function(row, peer, version) {
      var field_name = "info_prefixes"+version;

      var node = $("<input>")

      var input = new Peerctl.Application.APIInput(
        this.application.api,
        function() {
          return {"put":"peer/"+this.application.selected_network+
                 "/"+peer.port_id+
                 "/"+peer.id+
                 "/set_max_prefix/"};
        }.bind(this),
        {}
      ).payload(
        function(payload) {
          payload.ipv = version;
          return payload;
        }
      ).bind(node)
      input.element.val(peer[field_name])

      row.find("."+field_name+".holder").empty().append(node)
      input.show_indicator(node, "create");
      node.on("blur", function() { input.show_indicator(node, "create") })

    },

    "refresh_port_select" : function(asn) {
      var component = this;
      this.application.api.list("port/"+asn+"/", 0, function(ports) {
        this.input_select_port.empty();
        this.ports = {};
        $(ports).each(function() {
          component.input_select_port.append(
            $("<option>").prop("value",this.id).text(this.ix_name).attr('selected', (this.id==component.selected_port)));
          component.ports[this.id] = this;
        });
        if(!this.selected_port && ports.length) {
          this.select_port(ports[0].id);
        }
        if(!ports.length)
          this.refresh();
        this.load_device_info()
      }.bind(this));
    },

    "select_port" : function(port_id, from_input) {
      if(!from_input)
        this.input_select_port.val(port_id)
      this.selected_port = port_id;
      this.api_list.selected_port = port_id;
      this.api_object = this.ports[port_id];
      this.element.find(".nav-tabs").find('li a:first').tab('show');
      this.loading_shim.show();
      this.refresh();

      this.element.find(".ixcfg").mobileCollapse("collapse");
      $(this).trigger("port_change", [port_id]);
    },

    /**
     * Refresh the peer list from the api
     *
     * @method refresh
     */

    "refresh" : function() {
      if(this.selected_port == 0) {
        this.api_list.clear();
        this.loading_shim.hide()
        return;
      }
      this.loading_shim.show();
      this.api_list.refresh(function(data) {
        this.loading_shim.hide()
        this.update_counters();
      }.bind(this), function() { this.loading_shim.hide() }.bind(this));
      this.refresh_port_select(peerctl.selected_network);

    },

    "load_device_info" : function() {
      var asn = this.application.selected_network;
      var net = this.application.networks[asn];
      var port = this.selected_port;
      var application = window.peerctl;
      this.application.api.list("port/"+asn+"/"+port+"/devices/",{},function(data){
        var device = data[0];
        var port = this.ports[this.selected_port];
        var panel = this.container_device_info;

        panel.find('#port-name').text($fmt.device_name(port.ix_name, port));

        panel.find('#device-type').text(device.type);

        panel.find('#port-speed').text($fmt.speed(port.speed, port));

        panel.find('#port-policy4').empty().append(
          new Peerctl.Application.PolicySelect(function(port) {
            return "port/"+application.selected_network+
                   "/"+port.id+"/set_policy/";
          },
          port,
          function(){
          }.bind(this)).set_ip_version(4).refresh(port.policy4.id).element
        );

        panel.find('#port-policy6').empty().append(
          new Peerctl.Application.PolicySelect(function(port) {
            return "port/"+application.selected_network+
                   "/"+port.id+"/set_policy/";
          },
          port,
          function(){
          }.bind(this)).set_ip_version(6).refresh(port.policy6.id).element
        );


        panel.find("#device-type").empty().append(
          new Peerctl.Application.APIFieldChoiceSelect(
            "type",
            function(device) { return "device/0/" },
            function(device) { return "device/"+asn+"/"+device.id+"/" },
            device,
            function() {
              this.refresh();
            }.bind(this)
          ).payload(
            function(payload) {
              return {
                name: device.name,
                description: device.description,
                type: payload.value,
                asn: asn
              }
            }
          ).refresh(device.type).element
        );

        panel.find("#mac-address").empty().append(
          new Peerctl.Application.APIInput(
            application.api,
            function() {
              return { "put": "port/"+asn+"/"+port.id+"/set_mac_address/" }
            },
            {}
          ).bind($('<input>')).element.val(port.mac_address)
        );

        panel.find("#as-set").empty().append(
          new Peerctl.Application.APIInput(
            application.api,
            function() {
              return { "put": "net/"+asn+"/set_as_set/" }
            },
            {}
          ).bind($('<input>')).element.val(net.as_set)
        );


        panel.find('#device-template').empty().append(
          new Peerctl.Application.APISelect(
            application.api,
            function() {
              return { get: "devicetmpl/"+asn+"/list_available/" }
            },
            {
              param: {
                device_type: device.type
              }
            }
          ).bind($('<select>')).refresh().element
        );
      }.bind(this));
    },

    "device_template" : function() {
      return this.element.find("#device-template").find('select').val();
    },

    "update_counters" : function() {
      var peers_live = this.api_list.body.find(".item.bg-success").length;
      var peers_all = this.api_list.body.find(".item").length;
      var peers_avail = peers_all - peers_live;
      var peers_on_rs = this.api_list.body.find(".item.is-rs").length;


      this.element.find('#port-peers').text(peers_live);
      this.element.find('#port-available-peers').text(peers_avail);
      this.element.find('#port-rs-peers').text(peers_on_rs);
    },

    "mutual_locs_list" : function(peer, before_refresh, after_refresh) {
      var application = window.peerctl;
      var parent_list = this.api_list;
      var list = new Peerctl.Application.APIList(
        application.api,
        function(op, id, otherpeer){
          if(op == "list") {
            return "peer/"+application.selected_network+"/"+
                   "/"+this.selected_port+"/"+
                   "/"+peer.id+"/details/";
          } else {
            return this.api_list.path(op);
          }
        }.bind(this)
      ).bind(
        application.elements["list_net_"+this.tag+"_mutual"].clone(),
        application.elements["list_net_"+this.tag+"_mutual_item"]
      ).extend_list(
        this.api_list
      ).data_route(
        "mutual_locations"
      ).action(
        "add_peerses_other",
        {
          "loading_shim" : function(item) { return item.find(".item-container").first() },
          "path" : function(extra) {
            var otherpeer = extra.data;
            return "peerses/"+this.application.selected_network+
                   "/"+otherpeer.port_id+"/";
          }.bind(this),
          "action" : "create",
          "data" : function(otherpeer) {
            return { member : otherpeer.id }
          },
          "success" : function(data, all_data, sent_data) {
            this.list.update_or_add(data[0])
          }
        }
      ).action(
        "delete_peerses_other",
        {
          "loading_shim" : function(item) { return item.find(".item-container").first() },
          "path" : function(extra) {
            var otherpeer = extra.data;
            return "peerses/"+this.application.selected_network+
                   "/"+otherpeer.port_id+"/"+(otherpeer.peerses);
          }.bind(this),
          "action" : "delete",
          "confirm" : "Are you sure you want to remove this live session?",
          "success" : function(data, all_data, sent_data, extra) {
            var otherpeer = this.list.get_api_object(this.id)
            otherpeer.peerses_status = null
            this.list.update(otherpeer)
          }
        }
      ).formatter(
        "row", function(item, obj) {
          if(obj.peerses_status == "ok") {
            item.addClass("bg-success").removeClass("bg-normal")
            item.find(".uneditable").removeClass("uneditable").addClass("editable")
          } else {
            item.addClass("bg-normal").removeClass("bg-success")
            item.find(".editable").removeClass("editable").addClass("uneditable")
          }

          if(!obj.ipaddr6)
            item.find(".ipaddr6-toggle").hide();
          if(!obj.ipaddr4)
            item.find(".ipaddr4-toggle").hide();

          this.format_row_policy(item, obj, 4, function() {
            // refresh parent peer
            if(parent_list.index[obj.id])
              parent_list.refresh_item(obj.id);
          });
          this.format_row_policy(item, obj, 6, function() {
            // refresh parent peer
            if(parent_list.index[obj.id])
              parent_list.refresh_item(obj.id);
          });
        }.bind(this)
      )

      var prepare_ipaddr = function(e, obj) {
          var ipaddr = obj.ipaddr.length > 0 ? obj.ipaddr[0] : null;

          if(ipaddr) {
            obj.ipaddr4 = ipaddr.ipaddr4;
            obj.ipaddr6 = ipaddr.ipaddr6;
            obj.policy4 = ipaddr.policy4;
            obj.policy6 = ipaddr.policy6;
          }
      }
      $(list).on("row-add", prepare_ipaddr)
      $(list).on("row-update", prepare_ipaddr)

      $(list).on("before-refresh", before_refresh)
      $(list).on("after-refresh", after_refresh)

      list.refresh()
      return list;
    }
  },
  Peerctl.Application.Component
);

/**
 * @class TemplateEditorComponent
 * @extends Peerctl.Application.Component
 * @namspace Peerctl.NetworkApplication
 * @construtor
 */

Peerctl.NetworkApplication.TemplateEditorComponent = twentyc.cls.extend(
  "TemplateEditorComponent",
  {

    "TemplateEditorComponent" : function(application, component_name, tag) {
      var component = this;

      this.Component(application, component_name);

      this.tag = tag;

      this.container_form_add = this.element.find("#"+tag+"-add")
      this.container_form_edit = this.element.find("#"+tag+"-edit")

      application.api.meta(this.tag+"/0/", function(meta) {
        this.api_specs = meta;
        this.api_form_create.fill(
          application.elements["form_net_"+this.tag+"_add"],
          {
            type: meta.fields.type.choices[0].value
          },
          meta
        )
        this["select_type_create"].trigger("change");
      }.bind(this));


      /**
       * Use APIList widget to display the list of devices
       */
      this.api_list = new Peerctl.Application.APIList(
        application.api,
        function(){
          return this.tag+"/"+application.selected_network+"/";
        }.bind(this)
      ).bind(
        application.elements["list_net_"+this.tag],
        application.elements["list_net_"+this.tag+"_item"]
      ).action("edit", function(payload) {
        /*
         * edit action
         *
         * When a user clicks the edit button this action
         * will be called.
         */

        var tmpl_id = payload.id, tmpl = payload.data, item = payload.item;

        this.show_edit_template(tmpl, item);

        }.bind(this)
      );




      /*
       * Use APIForm widget to bind the html form for email template
       * creation to the API
       */
      this.api_form_create = new Peerctl.Application.APIForm(
        application.api,
        function(){ return component.tag+"/"+application.selected_network+"/" }
      ).bind(
        application.elements["form_net_"+this.tag+"_add"],
        "create",
        function(data) {
          // on successful creation add item to list
          this.api_list.add(data[0], true);
          // focus list tab
          this.element.find('[aria-controls="'+component.tag+'-list"]').tab("show");
        }.bind(this)
      )

      this.select_type_create = application.elements["form_net_"+this.tag+"_add"].find("#"+this.tag+"-type")


      this.select_type_create.change(function() {
        var body = application.elements["form_net_"+component.tag+"_add"].find("#"+component.tag+"-body");
        var name = application.elements["form_net_"+component.tag+"_add"].find("#"+component.tag+"-name");

        if(!$(this).val())
          return;

        component.loading_shim.show();

        $.get(
          "/tmpl/"+component.tag+"/"+$(this).val()+"/",
          function(data) {
            body.val(data);
            name.val("");
            component.loading_shim.hide()
          }
        ).fail(function() { component.loading_shim.hide() });
      });

      this.bind_preview(application.elements["form_net_"+this.tag+"_add"])


      /**
       * APIForm widget we will use for editing existing devices
       * (see above)
       */
      this.api_form_edit = new Peerctl.Application.APIForm(
        application.api,
        function(form){ return component.tag+"/"+application.selected_network+"/"+form.data(component.tag+"-id")+"/" }
      );


    },
    /**
     * Refresh the list from the api
     *
     * @method refresh
     */

    "refresh" : function() {
      this.api_list.refresh(function(data) {
        this.loading_shim.hide()
      }.bind(this), function() {
        this.loading_shim.hide();
      }.bind(this));
    },

    "show_edit_template" : function(tmpl, item) {
      // create new html form to use
      var application = this.application;
      var tmpl_id = tmpl.id;
      var container = application.elements["container_net_"+this.tag+"_edit"].
        clone();

      var form = container.find('.'+this.tag+'-form').
        data(this.tag+"-id", tmpl_id);

      this.bind_preview(form);

      // bind APIForm instance to new html form and fill
      // html form with current api object data
      this.api_form_edit.bind(
        form,
        "update",
        function(data) {
          // on successful update, update the row in the list
          this.api_list.update(data[0], true);
        }.bind(this)
      ).fill(form, item.data("api-object"), this.api_specs);

      this.container_form_add.hide();
      this.container_form_edit.empty().append(form).show();
    },

    "show_add_template" : function() {
      this.container_form_add.show();
      this.container_form_edit.empty().hide();
    },

    "bind_preview" : function(form) {
      var button = form.find('button[role="preview"]')
      var button_editor = form.find('button[role="editor"]')
      var body = form.find("#"+this.tag+"-body")
      var preview = form.find("#"+this.tag+"-preview")

      button.click(function() {
        preview.show();
        body.hide();
        button.addClass("active");
        button_editor.removeClass("active");
        this.preview(form);
      }.bind(this));

      button_editor.click(function() {
        preview.hide();
        body.show();
        button_editor.addClass("active");
        button.removeClass("active");
      }.bind(this));
    },

    "preview" : function(form) {
      var preview = form.find("#"+this.tag+"-preview")
      this.loading_shim.show();
      this.application.api.create(
        this.tag+"/"+this.application.selected_network+"/preview_blank/",
        {
          "type" : form.find("#"+this.tag+"-type").val(),
          "body" : form.find("#"+this.tag+"-body").val(),
          "device": peerctl.components.component_net_peer.api_object.device.id,
        },
        function(data) {
          preview.html(data[0].body);
          this.loading_shim.hide();
        }.bind(this),
        function(errors) {
          preview.html("ERRORS: "+errors);
          this.loading_shim.hide();
        }.bind(this)
      );
    }
  },
  Peerctl.Application.Component
);


Peerctl.NetworkApplication.DeviceTemplateComponent = twentyc.cls.extend(
  "DeviceTemplateComponent",
  {
    "DeviceTemplateComponent" : function(application, component_name) {
      this.TemplateEditorComponent(application, component_name, "devicetmpl");
      this.api_list.formatter("type", function(value, obj) {
        return value.replace(/-/g, " ");
      });
    }
  },
  Peerctl.NetworkApplication.TemplateEditorComponent
)

/**
 * `EmailTemplates` component in the network application
 *
 * Allows you to manage a network's peers
 *
 * @class EmailTemplateComponent
 * @extends Peerctl.Application.Component
 * @namspace Peerctl.NetworkApplication
 * @construtor
 */


Peerctl.NetworkApplication.EmailTemplateComponent = twentyc.cls.extend(
  "EmailTemplateComponent",
  {
    "EmailTemplateComponent" : function(application, component_name) {
      this.TemplateEditorComponent(application, component_name, "emltmpl");
      this.api_list.formatter("type", function(value, obj) {
        if(value == "peer-request")
          return "Peering Request"
        else if(value == "peer-config-complete")
          return "Peering Configuration Complete"
        else if(value == "peer-session-live")
          return "Peering Session Live"
      }.bind(this)).formatter("row", function(row, obj) {
        row.find(".global .icon").hide();
        row.find(".global .icon."+obj.type).show();
      });
    }
  },
  Peerctl.NetworkApplication.TemplateEditorComponent
)





/**
 * Holds classes for modal popups
 * @class Modals
 * @namespace Peerctl
 */

Peerctl.Modals = {};

/**
 * Modal popup base
 *
 * All modals should extend this class
 *
 * @class Base
 * @namespsace Peerctl.Modals
 * @constructor
 * @param {jQuery} jQuery - boot strap modal container
 * @param {String} title - modal title
 * @param {jQuery} content - modalcontent
 */

Peerctl.Modals.Base = twentyc.cls.define(
  "Base",
  {
    "Base" : function(jquery, title, content) {
      this.modal = jquery.clone();
      this.modal.appendTo(document.body);

      this.elements = {
        "title": this.modal.find('.modal-title'),
        "body": this.modal.find('.modal-body')
      }

      if(typeof(title) == "string")
        title = $('<span>').text(title);

      this.elements.title.empty().append(title);
      this.elements.body.append(content);
      this.modal.modal({show:false});
    },

    /**
     * Show the modal
     * @method show
     */

    "show" : function() {
      this.modal.modal("show");
    },

    /**
     * Hide the modal
     * @method hide
     */

    "hide" : function() {
      this.modal.modal("hide");
    }
  }
)

Peerctl.Modals.MD5Password = twentyc.cls.extend(
  "MD5Password",
  {
    "MD5Password" : function(application, peer, callback) {
      var modal = this;

      this.form = application.elements.form_md5password.clone();
      this.Base(application.elements.modal_display,
                $("<span>"+peer.name+"</span><small>MD5 Password</small>"),
                this.form);

      var input = this.form.find("input.md5")

/*
      this.input = new Peerctl.Application.APIInput(

*/
      this.api_form = new Peerctl.Application.APIForm(
        application.api,
        function() {
          return "peer/"+application.selected_network+
                 "/"+peer.port_id+
                 "/"+peer.id+
                 "/set_md5/"
        }
      ).bind(
        this.form,
        "update",
        function(data) {
          callback(data[0]);
          modal.hide();
        },
        function(data) { },
        this.modal.find('.save')
      );

      this.form.find(".copy-to-clipboard").click(function() {
        Peerctl.util.copy_to_clipboard(input.get(0));
        $(this).text("Copied")
      });

      input.val(peer.md5)
    }
  },
  Peerctl.Modals.Base
);


Peerctl.Modals.DeviceTemplate = twentyc.cls.extend(
  "DeviceTemplate",
  {
    "DeviceTemplate" : function(application, device, type, peer) {
      var modal = this;
      this.peer = peer;
      this.form = application.elements.form_devicetmpl_view.clone();
      this.Base(
        application.elements.modal_display,
        "Device Template",
        this.form
      )
      this.template_select = this.form.find('#template')
      var preview = this.preview = this.form.find("#preview")
      this.type = type;

      this.form.find(".copy-to-clipboard").click(function() {
        Peerctl.util.copy_to_clipboard(preview.get(0));
        $(this).text("Copied")
      });


      this.template_select.on("change", function() {

				let tmpl_id = $(this).val();
				let asn = application.selected_network;

				if(tmpl_id && tmpl_id != "0")
				  path = "devicetmpl/"+asn+"/"+tmpl_id+"/preview/";
				else
				  path = "devicetmpl/"+asn+"/preview_blank/";

        application.api.create(
				  path,
          {type:type, device:device.id, member:peer?peer.id:null},
          function(data) {
            modal.preview.html(data[0].body);
          }
        );
      });

      // fetch templates
      application.api.list(
        "devicetmpl/"+application.selected_network+"/",
        {},
        function(data) {
          var i = 0;
          this.template_select.empty();
          this.template_select.append(
            $('<option>').attr('value', 0).text("Default")
          );
          for(i = 0; i < data.length; i++) {
            if(data[i].type != this.type)
              continue;
            this.template_select.append(
              $('<option>').attr('value', data[i].id).text(data[i].name)
            );
          }
          this.template_select.trigger("change");
        }.bind(this)
      );

    }
  },
  Peerctl.Modals.Base
);

Peerctl.Modals.BulkEmail = twentyc.cls.extend(
  "BulkEmail",
  {
    "BulkEmail": function(application, ix) {
      this.application = application;
      this.form = application.elements.form_bulk_email.clone();
      this.ix = ix;
      this.reload_recipients();
      this.reload_replyto();

      var modal = this;

      this.Base(
        application.elements.modal_wizard,
        "Notification Email",
        this.form
      );

      this.form.find('#netname').text(application.selected_network_data.name);

      this.api_form = new Peerctl.Application.APIForm(
        application.api,
        function() {
          if(modal.step == "form")
            return "bulkemail/"+application.selected_network+"/preview/"
          else
            return "bulkemail/"+application.selected_network+"/"
        }
      ).bind(
        this.form,
        "create",
        function(data) {
          if(modal.step == "form") {
            this.preview(data[0]);
          } else {
            this.hide();
          }
        }.bind(this),
        function() {
          this.show_form();
        }.bind(this),
        this.modal.find('button.save')
      )

      this.modal.find('button.back').click(function() { this.show_form(); }.bind(this));

      this.show_form();

    },

    "show_form" : function() {
      this.elements.body.empty();
      this.elements.body.append(this.form)
      this.modal.find('button.save').text('Preview');
      this.modal.find('button.cancel').show();
      this.modal.find('button.back').hide();
      this.step = "form"
    },

    "preview" : function(data) {
      this.step = "preview"
      this.elements.body.empty();
      var preview = this.application.elements.bulk_email_preview.clone()

      this.list = new Peerctl.Application.APIList(
        this.application.api,
        function(){}.bind(this)
      ).bind(
        this.application.elements.bulk_email_preview_table,
        this.application.elements.bulk_email_preview_row
      ).refresh_data(data.recipients)

      preview.find("#recipients").append(this.list.container)
      preview.find("#count").text(data.recipients.length)
      preview.find("#role").text(data.role)
      preview.find("#replyto").text(data.replyto)
      this.elements.body.append(preview)

      this.modal.find('button.save').text('Send Email');
      this.modal.find('button.cancel').hide();
      this.modal.find('button.back').show();
    },

    "reload_recipients" : function() {

      var sel = this.form.find('#recipients');
      var ports = this.application.peers.ports, i, port;

      sel.append($('<option>').val("peers").text("All peers"));

      for(i in ports) {
        port = ports[i]
        if(port.ix_name)
          sel.append($('<option>').val("peers_at_ix:"+port.ix).text("Peers at "+port.ix_name).attr("selected", this.ix==port.ix));
      }
    },

    "reload_replyto" : function() {
      var sel = this.form.find("#replyto")
      var contacts = this.application.selected_network_data.contacts;
      sel.find('[data-net-contact]').each(function() {
        var contact = contacts[$(this).data('net-contact')];
        console.log("CONTACT", contact, this);
        if(contact) {
          $(this).text(contact).show();
        } else {
          $(this).hide();
        }
      })
      sel.find("option").first().attr("selected",true);
    }
  },
  Peerctl.Modals.Base
);


Peerctl.Modals.PeersesEmailWorkflow = twentyc.cls.extend(
  "PeersesEmailWorkflow",
  {
    "PeersesEmailWorkflow" : function(application, member, port, peer_list) {
      this.form = application.elements.form_peer_request_email.clone();
      this.member = member;

      var modal = this, current_step = "peer-request",
          title = "Peering Request";

      if(member.peerses_status == "requested") {
        title = "Notify Configuration Complete";
        current_step = "peer-config-complete";
      } else if(member.peerses_status == "configured") {
        title = "Notify Peering Session Live";
        current_step = "peer-session-live";
      }

      this.Base(
        application.elements.modal_submission_fullscreen,
        title,
        this.form
      );

      if(application.selected_network_data.peer_contact_email && member.peerses_contact && member.peerses_status != "ok") {
        // valid contact point for peering request exists. proceed
        this.form.find('#peer_contact').
          text(member.peerses_contact).
          attr("href", "mailto:"+member.peerses_contact);
        this.form.find("#peer_asn").text(member.asn);
        this.form.find("#peer_name").text(member.name);
        this.template_select = this.form.find('#template')
        this.preview = this.form.find("#preview")


        this.form.find('p.'+current_step).addClass("current-step")

        this.api_form = new Peerctl.Application.APIForm(
          application.api,
          "email_workflow/"+application.selected_network+"/"+
          port+"/"+member.id+"/"
        ).bind(
          this.form,
          "create",
          function(data) {
            this.hide();
            if(peer_list) {
              var i;
              for(i = 0; i<data.length; i++)
                peer_list.update(data[i], (data[i].peerses_status!="ok"));
            }
          }.bind(this),
          null,
          this.modal.find('button.save')
        );


        this.template_select.on("change", function() {

          let asn = application.selected_network;
          let tmpl_id = $(this).val();

          if(tmpl_id && tmpl_id != "0") {
            var path = "emltmpl/"+asn+"/"+tmpl_id+"/preview/";
          } else {
            var path = "emltmpl/"+asn+"/preview_blank/";
          }

          application.api.create(
            path,
            {type:current_step, peer:member.id, peerses:member.peerses},
            function(data) {
              modal.preview.html(data[0].body);
            }
          );
        });

        // fetch templates
        application.api.list(
          "emltmpl/"+application.selected_network+"/",
          {},
          function(data) {
            var i = 0;
            this.template_select.empty();
            this.template_select.append(
              $('<option>').attr('value', 0).text("Default")
            );
            for(i = 0; i < data.length; i++) {
              if(data[i].type != current_step)
                continue;
              this.template_select.append(
                $('<option>').attr('value', data[i].id).text(data[i].name)
              );
            }
            this.template_select.trigger("change");
          }.bind(this)
        );
      } else {
        this.form.empty();
        var msg = "";
        if(!member.peerses_contact) {
          // valid contact point for peering request does not exist. bail
          msg = "Could not find email contact for the specified peer";
        } else if(member.peerses_status == "ok") {
          msg = "You already have a peer session with this peer";
        } else if(!application.selected_network_data.peer_contact_email) {
          msg = "You do not provide a 'Policy' role contact at your peeringdb entry. It is required as it will be used as the Reply-To address for any emails sent during the peering session setup. Please add one and try again later";
        }
        this.form.append($("<div>").html(msg));
        this.modal.find('button.save').detach();
      }
    }
  },
  Peerctl.Modals.Base
);

/**
 * Modal popup to submit a feature request
 *
 * @class MakeAWish
 * @namespace Peerctl.Modals
 * @constructor
 * @param {Peerctl.Application} application
 */

Peerctl.Modals.MakeAWish = twentyc.cls.extend(
  "MakeAWish",
  {
    "MakeAWish" : function(application) {
      this.form = application.elements.form_make_a_wish.clone();
      this.Base(
        application.elements.modal_submission,
        "Make a Wish",
        this.form
      );

      this.api_form = new Peerctl.Application.APIForm(
        application.api,
        "wish/"
      ).bind(this.form, "create", function() { this.hide() }.bind(this),  null, this.modal.find('button.save'))

    },

    /**
     * Shows the make a wish modal for a feature request for the
     * specified component name
     *
     * @method show
     * @param {String} component - component name suche as 'device'
     */

    "show" : function(component) {
      this.api_form.fill(this.form, {path:component}, {fields:{path:{choices:[
        { value : "peer", display_name : "Peering List" },
        { value : "emltmpl", display_name : "Email Templates" },
        { value : "devicetmpl", display_name : "Device Templates" },
        { value : "policy", display_name : "Policies" }
      ]}}});
      this.Base_show();
    },

    "bind" : function(component) {
      component.menu_add("Tools", "Make a Wish", function() { this.show(component.tag); }.bind(this), "heart");
    }
  },
  Peerctl.Modals.Base
);


/**
 * Modal popup to manage user preferences
 *
 * @class UserPreferences
 * @namespace Peerctl.Modals
 * @constructor
 * @param {Peerctl.Application} application
 */

Peerctl.Modals.UserPreferences = twentyc.cls.extend(
  "UserPreferences",
  {
    "UserPreferences" : function(application) {
      this.form = application.elements.form_userpref.clone();
      this.api = application.api;
      this.Base(
        application.elements.modal_submission,
        "User Preferences",
        this.form
      );

      this.api_form = new Peerctl.Application.APIForm(
        application.api,
        "userpref/0/"
      ).bind(this.form, "update", function() { this.hide() }.bind(this),  null, this.modal.find('button.save'))
    },

    "show" : function() {
      this.api.list("userpref/", {}, function(data) {
        this.api_form.fill(this.form, data[0], {});
        this.Base_show();
      }.bind(this));
    }
  },
  Peerctl.Modals.Base
);


$(document).ready(function() {
  window.peerctl = new Peerctl.NetworkApplication();
  Peerctl.instance = window.peerctl;

  $('[data-sort-target]').each(function() {
    if($(this).children('span.asc').length == 0) {
      $(this).append(
        $('<span> </span>'),
        $('<span class="asc glyphicon glyphicon-chevron-down"></span>'),
        $('<span class="desc glyphicon glyphicon-chevron-up"></span>')
      );
    }
  });

  if(Peerctl.device_size == "xs") {
    $('.mobile-row').addClass("row")
    $('.mobile-col-label').addClass("col-xs-4")
    $('.mobile-col-value').addClass("col-xs-8")
  }

  $('.menu-container').mobileCollapse();
  $('.menu-container').mobileCollapse("collapse");

  twentyc.listutil.sortable.init();
  twentyc.listutil.filterable.init();
});

$util.device_size = function() {
  var div = $("#users-device-size").first().find("div:visible").first()
  return div.attr("id")
}

Peerctl.device_size = $util.device_size();

twentyc.jq.plugin("mobileCollapse", {
  "init" : function() {
    if(Peerctl.device_size != "xs")
      return;
    this.find(".mobile-collapse-indicator").click(function() {
      $(this).parent().mobileCollapse("toggle");
    });
  },

  "toggle": function() {
    if(Peerctl.device_size != "xs")
      return
    var indicator = this.find(".mobile-collapse-indicator.expanded").first();
    if(indicator.length == 0)
      this.mobileCollapse("expand")
    else
      this.mobileCollapse("collapse")
  },

  "collapse" : function() {
    if(Peerctl.device_size != "xs")
      return
    var indicator = this.find(".mobile-collapse-indicator").first();
    this.find("[data-mobile-collapse]").each(function() {
      $(this).hide().removeClass("expanded");
    });
    indicator.removeClass("expanded").find(".indicator-label").first().html(indicator.data("text-collapsed"));
    indicator.find(".indicator-icon").attr("src", indicator.data("icon-collapsed"))
  },

  "expand" : function() {
    if(Peerctl.device_size != "xs")
      return
    var indicator = this.find(".mobile-collapse-indicator").first();
    this.find("[data-mobile-collapse]").each(function() {
      $(this).show().addClass("expanded");
    });

    indicator.addClass("expanded").find(".indicator-label").first().html(indicator.data("text-expanded"));
    indicator.find(".indicator-icon").attr("src", indicator.data("icon-expanded"))
  }

})


})(jQuery, twentyc);
