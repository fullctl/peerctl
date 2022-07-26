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
  }
};

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
    if(value.match(/^netixlan(\d+)$/)) {
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
        console.log("ERROR", errors);
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
            for(i in this.value)
              $('<p>').appendTo(misc.find('.panel-body')).text(this.value[i]);
            element.prepend(misc)
          }
        });
      }
      return this.error_handler(callback);
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
        if(config.action == "delete") {
          this[config.action](config.path(extra), success, error, config.render_errors_to);
        } else {
          this[config.action](config.path(extra), config.data(extra), success, error, config.render_errors_to);
        }
      }.bind(this);
      return send_request;
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
        if(callback)
          callback(response, error, data);
        $(errors).each(function() {
          var par = form.find('[name="'+this.name+'"]').parents('.form-group');
          par.addClass('has-error has-feedback');
          $('<span class="help-block validation-error">').text(this.value).appendTo(par)
          $('<span class="glyphicon glyphicon-remove validation-error form-control-feedback">').appendTo(par)

          if(this.name == "non_field_errors" || this.name == "detail") {
            var i, misc = $('<p class="bg-danger validation-error">');
            var nfe_container = form.find(".non-field-errors")
            for(i in this.value)
              $('<p>').appendTo(misc).text(this.value[i]);
            if(nfe_container.length)
              nfe_container.append(misc)
            else
              form.prepend(misc)
          }
        });
      }
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
          this.path(form), data, callback, this.error_handler(form, error)
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
    "bind" : function(select, onupdate) {
      var widget = this;
      this.element = select;
      this.element.on("change", function() {
        var payload = widget.payload_handler({"value": $(this).val() });
        var callback = widget.path().put
        if(typeof callback == "function") {
          callback(payload);
        } else if(callback) {
          widget.api.update(
            callback, payload, onupdate);
        }
      });
      return this;
    },
    "refresh" : function(value) {
      if(typeof value != "undefined") {
        this.value = value;
        console.log("UPDATING VALUE", value, this);
      }
      this.api.list(this.path().get, this.param, function(data) {
        this.fill(data)
      }.bind(this));
      return this;
    },
    "payload" : function(handler) {
      this.payload_handler = handler;
      return this;
    },
    "fill" : function(data) {
      var widget = this, i;
      widget.element.empty();

      for(i = this.prepend.length-1; i >= 0; i--) {
        data.unshift(this.prepend[i]);
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
  Peerctl.Application.APIWidget
);


Peerctl.Application.PolicySelect = twentyc.cls.extend(
  "PolicySelect",
  {
    "PolicySelect" : function(put_path, api_object, refresh) {
      var application = window.peerctl;
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
            { "id" : 0, "name" : "Inherit" }
          ]
        }
      )
      this.bind($('<select>').addClass("policy-select"), function(data) {
        if(refresh)
          refresh(data[0], api_object);
      }.bind(this))
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
      this.container = container;
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
     * @param {Function} callback
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
      if(this[name])
        throw("Action "+name+" has already been added to "+this);
      this.actions[name] = callback;
      if(typeof callback == "function") {
        this[name] = callback.bind(this);
      } else if(typeof callback == "object") {
        var list = this;
        callback.render_errors_to = this.container.parent();
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
          open(api_object, item, this);
        }.bind(this));
      }
      return this;
    },

    "option_policy_select" : function(put_path, refresh) {
      return this.option_complex(
        "Set Policy",
        function(api_object, item, api_list) {
          var application = window.peerctl;
          var select = new Peerctl.Application.APISelect(
            application.api,
            function() {
              return {
                get: "policy/"+application.selected_network+"/",
                put: put_path(api_object, api_list)
              };
            },
            {
              prepend: [
                { "id" : 0, "name" : "Inherit" }
              ]
            }
          )

          select.value = api_object.policy.inherited ? 0 : api_object.policy.id;
          select.bind($('<select>').addClass("option-select"), function(data) {
            if(refresh)
              refresh(data[0], api_object, api_list);
          }.bind(this))

          item.data('policy_select', select);
          return select.element;
        }.bind(this),
        function(api_object, item) {
          item.data('policy_select').refresh();
        }
      );
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
        var k,
            item = this.item_template.clone(),
            widget = this;

        item.attr("data-row-id", api_object.id).
          attr("id", "row-"+api_object.id).
          data("api-object", api_object)

        item.find('button[data-action]').each(function() {
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

        for(k in api_object) {
          item.find('[name="'+k+'"]').
            html(this.format(k, api_object)).
            attr("data-sort-value", api_object[k]);
        }
        item.appendTo(this.body);
        this.index[api_object.id] = item;
        this.format_row(api_object);
        if(effect)
          this.mark_item_new(item);
      }
      this.sort()
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
      if(!item)
        return;
      for(k in api_object) {
        item.find('[name="'+k+'"]').html(this.format(k, api_object));
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
      this.api.list(this.path("list"), null, function(_data) {
        console.log("Data returned "+(new Date().getTime()-ts)+"ms");
        widget.clear();
        var i, data = widget._data_route(_data);

        for(i = 0; i < data.length; i++) {
          widget.update_or_add(data[i]);
        }
        widget.apply_filters();
        if(callback)
          widget.sort_timer.ready(function() { callback(data); });

        var ts2 = new Date().getTime();
        console.log("Finished after "+(ts2-ts)+" ms");
      }, error, this.container.parent());
      return this;
    },

    "refresh_item" : function(id) {
      this.api.retrieve(this.path("retrieve")+"/"+id+"/", {}, function(data) {
        this.update_or_add(data)
      }.bind(this));
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
      this.element = application.elements[component_name];
      this.loading_shim = $('<div>').addClass("loading-shim").
        appendTo(this.element).append($('<div>').html("Loading").prepend($("<img>").prop("src", Peerctl.STATIC_URL+"loading.gif"))).hide();
      this.tag = "component"
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

    /**
     * Adds an item into a menu section
     *
     * @method menu_add
     * @param {String} section_name
     * @param {String} label: item label
     * @param {Function} callback: on click
     */

    "menu_add": function(section_name, label, callback, glyphicon) {
      if(typeof label == "string")
        label = $('<span>').text(label);

      if(!this.menu_button) {
        this.menu_button = this.element.find("#btn-"+this.tag+"-menu");
        this.menu_button.mousedown(function() { $(this).trigger("menu_open") }.bind(this));
      }

      if(glyphicon) {
        $('<span> </span>').prependTo(label);
        $('<span>').addClass("glyphicon glyphicon-"+glyphicon).
        prependTo(label);
      }


      $('<li>').
        append($('<a>').
        append(label)).
        insertAfter(this.menu_section(section_name)).
        click(callback);
    },

    "menu_add_complex": function(section_name, content, open, glyphicon) {
      var content_node = content()
      content_node.click(function(e) { e.stopPropagation(); });
      content_node.mousedown(function(e) { e.stopPropagation(); });
      this.menu_add(section_name, content_node, glyphicon)
      if(open)
        $(this).on("menu_open", open)
    }


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
      this.navmenu_add("User", "Preferences", function() { this.user.show() }.bind(this), "cog");
      this.selected_network = 0;
      this.load_networks();
      this.devices = new Peerctl.NetworkApplication.DeviceComponent(this, "component_net_device");
      this.policies = new Peerctl.NetworkApplication.PolicyComponent(this, "component_net_policy");
      this.ports= new Peerctl.NetworkApplication.PortComponent(this, "component_net_port");
      this.peers= new Peerctl.NetworkApplication.PeerComponent(this, "component_net_peer");
      this.email_templates = new Peerctl.NetworkApplication.EmailTemplateComponent(this, "component_net_email_template");
      this.device_templates = new Peerctl.NetworkApplication.DeviceTemplateComponent(this, "component_net_device_template");
      this.make_a_wish = new Peerctl.Modals.MakeAWish(this);
      this.user = new Peerctl.Modals.UserPreferences(this);
      this.make_a_wish.bind(this.devices);
      this.make_a_wish.bind(this.ports);
      this.make_a_wish.bind(this.peers);
      this.make_a_wish.bind(this.email_templates);
      this.make_a_wish.bind(this.device_templates);
      this.make_a_wish.bind(this.policies);
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
      this.email_templates.refresh();
      this.device_templates.refresh();
      document.location.href = "#"+asn;
      $(this).trigger('network_change', [asn]);
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
      var preferred_network = $util.url_anchor(parseInt);
      this.api.list("/net", null, function(data) {
        $(Peerctl.util.sort(data, "name", true)).each(function() {
          instance.navmenu_add("Networks", this.name || (this.asn + " (Network Data Missing)"), function() { instance.select_network(this.asn, this) }.bind(this));
          instance.networks[this.asn] = this;
          if(!instance.selected_network) {
            if(!preferred_network || preferred_network == this.asn)
              instance.select_network(this.asn, this);
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
          "net/"+application.selected_network+"/device/"+device_id+"/port"
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
            "device_template/"+application.selected_network+"/list_available/",
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

      this.tag = "policy"

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
      ).formatter("name", function(value, api_object)
        {
          if(api_object.is_global)
            return value+" (global)";
          return value;
        }.bind(this)
      ).action("edit", function(payload) {
        /*
         * edit action
         *
         * When a user clicks the edit button this action
         * will be called.
         */

        var policy_id = payload.id, policy = payload.data, item = payload.item;

        // create new html form to use
        var container = application.elements.container_net_policy_edit.
          clone();

        var form = container.find('.policy-form').
          data("policy-id", policy_id);

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
          }.bind(this)
        ).fill(form, item.data("api-object"), this.api_specs);

        // add tab for the policy and focus it
        this.get_or_add_tab("policy-"+policy_id, policy.name, container, true);
        }.bind(this)
      );


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
          // focus list tab
          this.element.find('[aria-controls="policy-list"]').tab("show");
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
        function(){ return "port/"+application.selected_network }
      ).bind(
        application.elements.list_net_port,
        application.elements.list_net_port_item
      ).formatter(
        "speed", $fmt.speed
      ).formatter(
        "policy", $fmt.policy
      ).option_policy_select(
        function(api_object) {
          return "port/"+application.selected_network+
                 "/"+api_object.id+"/set_policy/"
        },
        function(port) {
          this.api_list.update(port, true);
          application.peers.refresh();
        }.bind(this)
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

      this.btn_device_config.click(function() {
         new Peerctl.Modals.DeviceTemplate(
             application, this.api_object.device, this.device_template()).show();
      }.bind(this));

      this.input_select_port.on("change", function() {
        component.select_port($(this).val(), true);
      });

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
      ).formatter(
        "asn", $fmt.peeringdb
      ).formatter(
        "policy", $fmt.policy
      ).formatter(
        "peer_session_status", function(value, api_object) {
          if(value == "ok")
            return "live"
          else if(value == "" || !value)
            return "-"
          else
            return value
        }
      ).action(
        "add_peer",
        {
          "path" : function() {
            return "net/"+this.application.selected_network+
                   "/port/"+this.selected_port+"/peer_session/";
          }.bind(this),
          "action" : "create",
          "data" : function(peer) {
            return { netixlan : peer.id }
          },
          "success" : function(data, all_data, sent_data) {
            this.list.refresh_item(this.id);
          }
        }
      ).action(
        "delete_peer",
        {
          "path" : function(peer) {
            return "net/"+this.application.selected_network+
                   "/port/"+this.selected_port+"/peer_session/"+(peer.data.peer_session);
          }.bind(this),
          "action" : "delete",
          "success" : function(data, all_data, sent_data) {
            this.list.refresh_item(this.id);
          }
        }

      ).action(
        "email_peer",
        function(item) {
          var modal = new Peerctl.Modals.PeersesEmailWorkflow(this.application, item.data, this.selected_port, this.api_list);
          modal.show();
        }.bind(this)
      ).action(
        "peer_details",
        function(item) {
          var container = application.elements["container_net_"+this.tag+"_details"].clone();
          var api_object = item.data;
          var mutual_locs = this.mutual_locs_list(api_object);
          container.find('#mutual-loc').append(mutual_locs.container);
          container.find('#peer-name').text(api_object.name);
          container.find('#peer-asn').text(api_object.asn);
          container.find('#peer-asn').text(api_object.asn);
          container.find('#peer-scope').text(api_object.scope);
          container.find('#peer-type').text(api_object.type);
          container.find('#peer-prefixes-4').text(api_object.info_prefixes4);
          container.find('#peer-prefixes-6').text(api_object.info_prefixes6);
          container.find('#btn-peer-request').click(function() {
            this.api_list.email_peer({
              "list" : this.api_list,
              "data" : api_object,
              "id" : api_object.id,
              "item" : this.api_list.get(api_object.id)
            })
          }.bind(this));
          this.get_or_add_tab(api_object.id, api_object.name, container, true);
        }.bind(this)
      ).formatter(
        "row", function(row, api_object) {
          if(api_object.peer_session_status == "ok") {
            row.addClass("bg-success").removeClass("bg-normal");
          } else {
            row.removeClass("bg-success").addClass("bg-normal");
          }
          row.find("td.filters").attr("data-filter-value-peer_session", api_object.peer_session);
        }
      ).option(
        "Stop Session",
        function(peer, item, api_list) {
          api_list.delete_peer({
            "list" : api_list,
            "data" : item.data("api-object"),
            "id" : peer.id,
            "item" : item
          });
        }.bind(this),
        "remove-circle"
      ).option_policy_select(
        function(peer, api_list) {
          return "net/"+application.selected_network+
                 "/port/"+this.selected_port+
                 "/peer_session/"+peer.peer_session+"/set_policy/";
        }.bind(this),
        function(peer_session, peer, api_list) {
          api_list.refresh_item(peer.id)
        }.bind(this)
      ).formatter(
        "name", function(value, api_object) {
          var node = $('<span>');
          var link = $('<a>').text(value).addClass("action")

          link.click(function() {
            this.api_list.peer_details({
              "list" : this.api_list,
              "data" : api_object,
              "id" : api_object.id,
              "item" : this.api_list.get(api_object.id)
            });
          }.bind(this));

          node.append(link);
          node.append($('<br>')).append($('<small>').text((api_object.ipaddr4 || api_object.ipaddr6 || "")));
          return node;
        }.bind(this)
      )
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
      var port = this.selected_port;
      var application = window.peerctl;
      this.application.api.list("port/"+asn+"/"+port+"/devices/",{},function(data){
        var device = data[0];
        var port = this.ports[this.selected_port];
        var panel = this.container_device_info;
        panel.find('#port-name').text($fmt.device_name(port.ix_name, port));
        panel.find('#device-type').text(device.type);
        panel.find('#port-speed').text($fmt.speed(port.speed, port));
        panel.find('#port-policy').empty().append(
          new Peerctl.Application.PolicySelect(function(port) {
            return "net/"+application.selected_network+
                   "/port/"+port.id+"/set_policy/";
          },
          port,
          function(){
            this.refresh();
          }.bind(this)).refresh(port.policy.id).element
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

        panel.find('#device-template').empty().append(
          new Peerctl.Application.APISelect(
            application.api,
            function() {
              return { get: "device_template/"+asn+"/list_available/" }
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
      var peers_live = this.api_list.body.find("tr.bg-success").length;
      var peers_all = this.api_list.body.find("tr").length;
      var peers_avail = peers_all - peers_live;


      this.element.find('#port-peers').text(peers_live);
      this.element.find('#port-available-peers').text(peers_avail);
    },

    "mutual_locs_list" : function(peer) {
      var application = window.peerctl;
      return new Peerctl.Application.APIList(
        application.api,
        function(op){
          if(op == "list") {
            return "net/"+application.selected_network+"/"+
                   "port/"+this.selected_port+"/"+
                   "peer/"+peer.id+"/details/";
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
      ).formatter(
        "port", function(value, obj) { return value.ix_name; }
      ).refresh()
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

        // create new html form to use
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
            // focus the list tab
            this.tab(this.tag+'-list').tab('show');
            // close the edit tab
            this.close_tab(this.tag+"-"+tmpl_id);
          }.bind(this)
        ).fill(form, item.data("api-object"), this.api_specs);

        // add tab for the tmpl and focus it
        this.get_or_add_tab(this.tag+"-"+tmpl_id, tmpl.name, container, true);
        }.bind(this)
      );




      /*
       * Use APIForm widget to bind the html form for email template
       * creation to the API
       */
      this.api_form_create = new Peerctl.Application.APIForm(
        application.api,
        function(){ return "net/"+application.selected_network+"/"+component.tag+"/" }
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
        function(form){ return "net/"+application.selected_network+"/"+component.tag+"/"+form.data(component.tag+"-id")+"/" }
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
      }.bind(this), function() { this.loading_shim.hide() }.bind(this));
    },

    "bind_preview" : function(form) {
      var button = form.find('button[role="preview"]')
      var body = form.find("#"+this.tag+"-body")
      var preview = form.find("#"+this.tag+"-preview")

      button.click(function() {
        if(body.is(":visible")) {
          body.hide();
          preview.show();
          button.text("Editor");
          this.preview(form);
        } else {
          preview.hide();
          body.show();
          button.text("Preview");
        }
      }.bind(this));
    },

    "preview" : function(form) {
      var preview = form.find("#"+this.tag+"-preview")
      this.loading_shim.show();
      this.application.api.create(
        "net/"+this.application.selected_network+"/"+this.tag+"/0/preview/",
        {
          "type" : form.find("#"+this.tag+"-type").val(),
          "body" : form.find("#"+this.tag+"-body").val()
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
      this.TemplateEditorComponent(application, component_name, "device_template");
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
      this.TemplateEditorComponent(application, component_name, "email_template");
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
      this.modal.find('.modal-title').text(title);
      this.modal.find('.modal-body').append(content);
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


Peerctl.Modals.DeviceTemplate = twentyc.cls.extend(
  "DeviceTemplate",
  {
    "DeviceTemplate" : function(application, device, type) {
      var modal = this;

      this.form = application.elements.form_device_template_view.clone();
      this.Base(
        application.elements.modal_display,
        "Device Template "+device.id+" "+type,
        this.form
      )
      this.template_select = this.form.find('#template')
      this.preview = this.form.find("#preview")
      this.type = type;

      this.preview.focus(function() { $(this).select(); });

      this.template_select.on("change", function() {
        application.api.create(
          "net/"+application.selected_network+"/device_template/"+$(this).val()+"/preview/",
          {type:type, device:device.id},
          function(data) {
            modal.preview.html(data[0].body);
          }
        );
      });

      // fetch templates
      application.api.list(
        "net/"+application.selected_network+"/device_template/",
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


Peerctl.Modals.PeersesEmailWorkflow = twentyc.cls.extend(
  "PeersesEmailWorkflow",
  {
    "PeersesEmailWorkflow" : function(application, netixlan, port, peer_list) {
      this.form = application.elements.form_peer_request_email.clone();
      this.netixlan = netixlan;

      var modal = this, current_step = "peer-request",
          title = "Peering Request";

      if(netixlan.peer_session_status == "requested") {
        title = "Notify Configuration Complete";
        current_step = "peer-config-complete";
      } else if(netixlan.peer_session_status == "configured") {
        title = "Notify Peering Session Live";
        current_step = "peer-session-live";
      }

      this.Base(
        application.elements.modal_submission,
        title,
        this.form
      );

      if(application.selected_network_data.peer_contact_email && netixlan.peer_session_contact && netixlan.peer_session_status != "ok") {
        // valid contact point for peering request exists. proceed
        this.form.find('#peer_contact').
          text(netixlan.peer_session_contact).
          attr("href", "mailto:"+netixlan.peer_session_contact);
        this.form.find("#peer_asn").text(netixlan.asn);
        this.form.find("#peer_name").text(netixlan.name);
        this.template_select = this.form.find('#template')
        this.preview = this.form.find("#preview")


        this.form.find('p.'+current_step).addClass("current-step")

        this.api_form = new Peerctl.Application.APIForm(
          application.api,
          "net/"+application.selected_network+"/port/"+
          port+"/peer/"+netixlan.id+"/email_workflow/"
        ).bind(
          this.form,
          "create",
          function(data) {
            this.hide();
            if(peer_list) {
              var i;
              for(i = 0; i<data.length; i++)
                peer_list.update(data[i], (data[i].peer_session_status!="ok"));
            }
          }.bind(this),
          null,
          this.modal.find('.btn-submit')
        );


        this.template_select.on("change", function() {
          application.api.create(
            "email_template/"+application.selected_network+"/"+$(this).val()+"/preview/",
            {type:current_step, peer:netixlan.id, peer_session:netixlan.peer_session},
            function(data) {
              modal.preview.html(data[0].body);
            }
          );
        });

        // fetch templates
        application.api.list(
          "email_template/"+application.selected_network+"/",
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
        if(!netixlan.peer_session_contact) {
          // valid contact point for peering request does not exist. bail
          msg = "Could not find email contact for the specified peer";
        } else if(netixlan.peer_session_status == "ok") {
          msg = "You already have a peer session with this peer";
        } else if(!application.selected_network_data.peer_contact_email) {
          msg = "You do not provide a 'Policy' role contact at your peeringdb entry. It is required as it will be used as the Reply-To address for any emails sent during the peering session setup. Please add one and try again later";
        }
        this.form.append($("<div>").html(msg));
        this.modal.find('.btn-submit').detach();
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
      ).bind(this.form, "create", function() { this.hide() }.bind(this),  null, this.modal.find('.btn-submit'))

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
        { value : "port", display_name : "Ports" },
        { value : "peer", display_name : "Peers" },
        { value : "email_template", display_name : "Email Templates" },
        { value : "device_template", display_name : "Device Templates" },
        { value : "policy", display_name : "Policies" },
        { value : "device", display_name : "Devices" }
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
      this.form = application.elements.form_user.clone();
      this.api = application.api;
      this.Base(
        application.elements.modal_submission,
        "User Preferences",
        this.form
      );

      this.api_form = new Peerctl.Application.APIForm(
        application.api,
        "user/0/"
      ).bind(this.form, "update", function() { this.hide() }.bind(this),  null, this.modal.find('.btn-submit'))
    },

    "show" : function() {
      this.api.list("user/", {}, function(data) {
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

  twentyc.listutil.sortable.init();
  twentyc.listutil.filterable.init();
});


})(jQuery, twentyc);
