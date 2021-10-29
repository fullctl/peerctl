/**
 * Filter controls for content
 *
 * Dependencies:
 *   1. jquery >= 1.11.13
 *   2. twentyc.core.js
 */

(function($) {

tc.u.require_namespace("twentyc.listutil");


twentyc.listutil.filterable = {
  test_classes : {},
  init : function(opt) {

    // collect all filters and connect them to
    // their respective targets

    $('[data-filter-target]').each(function() {
      var me = $(this);
      var target = $($(me).data("filter-target"));
      var test = $(me).data("filter-test") || "Equal";
      var filters = target.data("filters") || [];
      var id = $(me).data("filter-id");
      var mode = $(me).data("filter-mode");

      if(!id) {
        throw "Filters need to have data-filter-id attribute";
      }

      var filter = {
        "test_object" : new $filterable.test_classes[test](),
        "input" : $filterable.input_handlers.get_best(me, target),
        "id" : id,
        "mode" : mode,
        "test" : function(row_value) {
          return this.test_object.test(row_value, this.input.value());
        },
        "action" : $(me).data("filter-action") || "show"
      }
      if(!filter.input)
        throw "Could not find input handler for "+me;
      filters.push(filter);
      target.data("filters", filters);
    });

    // default options
    this.opt = {
      "row_selector" : ".item",
      "delay" : 100
    }

    // option override
    if(opt) {
      var prop;
      for(prop in opt)
        this.opt[prop] = opt[prop];
    }
  }
}

// for convenience
$filterable = twentyc.listutil.filterable;

$filterable.input_handlers = new twentyc.cls.Registry();

$filterable.input_handlers.get_best = function(input, target) {
  var k;
  for(k in this._classes) {
    if(this._classes[k].prototype.applicable(input)) {
      var r = new this._classes[k](input, target);
      r.bind(input, target);
      return r;
    }
  }
  return null;
}

$filterable.input_handlers.register(
  "Text",
  {
    "Text" : function(input, target) {
      this.input = input;
    },
    "applicable" : function(input) {
      return input.prop("type") == "text";
    },
    "value" : function() {
      return this.input.val();
    },
    "bind" : function(input, target) {
      input.on("keyup", function() {
        callback = function() { target.filterable("filter"); };
        if(!this.delay) {
          this.delay = new twentyc.util.SmartTimeout(callback, $filterable.opt.delay);
        } else {
          this.delay.set(callback, $filterable.opt.delay);
        }
      }.bind(this));
    }
  }
);

$filterable.input_handlers.register(
  "Checkbox",
  {
    "Checkbox" : function(input, target) {
      this.input = input;
    },
    "applicable" : function(input) {
      return input.prop("type") == "checkbox";
    },
    "value" : function(){
      return this.input.prop("checked");
    },
    "bind" : function(input, target) {
      input.on("change", function() { target.filterable("filter"); });
    }
  },
  $filterable.input_handlers.Text
);

/**
 * Filter tests
 */

$filterable.test_classes.Base = twentyc.cls.define(
  "Base",
  {
    "prepare_value" : function(value) {
      return value;
    },

    "test" : function(row_value, input_value) {
      return row_value == input_value;
    }
  }
);

$filterable.test_classes.IsEqual = twentyc.cls.extend(
  "Equal",
  {},
  $filterable.test_classes.Base
);

$filterable.test_classes.IsTrue = twentyc.cls.extend(
  "IsTrue",
  {
    "prepare_value" : function(value) {
      return Boolean(parseInt(value));
    },

    "test" : function(row_value, input_value) {
      return this.prepare_value(row_value) == true;
    }
  },
  $filterable.test_classes.Base
);

$filterable.test_classes.IsFalse = twentyc.cls.extend(
  "IsFalse",
  {
    "test" : function(row_value, input_value) {
      return this.prepare_value(row_value) == false;
    }
  },
  $filterable.test_classes.IsTrue
);

/**
 * jQuery plugin
 */

twentyc.jq.plugin(
  "filterable",
  {
    "init": function() {},
    "filter" : function() {
      this.each(function() {
        var me = $(this);
        var filters = me.data("filters");

        if(!filters)
          return;

        // process rows
        me.find($filterable.opt.row_selector).each(function() {
          var row = {"element" : $(this), "show" : false}

          // apply filters
          $(filters).each(function() {
            var filter = this;
            var additive = filter.mode == "additive";

            // cycle through filter values for row
            row.element.find('[data-filter-value-'+filter.id+']').each(
              function() {
                var row_value = $(this).attr("data-filter-value-"+filter.id);
                if(filter.test(row_value)) {
                  if(filter.action == "show") {
                    if(filter.input.value())
                      row.show = (additive ? row.show : true);
                    else
                      row.show = false;
                  }
                }
              }
            );
          });

          if(row.show) {
            row.element.show();
          } else {
            row.element.hide();
          }

        });
      });
    }
  }
);

})(jQuery);
