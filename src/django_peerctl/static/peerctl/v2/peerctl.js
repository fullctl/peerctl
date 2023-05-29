(function($, $tc, $ctl) {

var $peerctl = $ctl.application.Peerctl = $tc.extend(
  "Peerctl",
  {
    Peerctl: function() {
      this.Application("peerctl");

      if(!this.application_access_granted) {
        return;
      }

      this.autoload_page();

      // init home page tool

      this.tool("home", () => {
        return new $peerctl.Home();
      });
			
      // init peering lists tool

      this.tool("peering_lists", () => {
        return new $peerctl.PeeringLists();
      });

      // init network search tool 

      this.tool("networks", () => {
        return new $peerctl.Networks();
      });

      // init network settings tool

      this.tool("network_settings", () => {
        return new $peerctl.NetworkSettings();
      });

      // init ix tool

      this.tool("ix", () => {
        return new $peerctl.Ix();
      });

      // init sessions summary tool

      this.tool("sessions_summary", () => {
        return new $peerctl.SessionsSummary();
      });

      // init policies management tool

      this.tool("policies", ()=> {
        return new $peerctl.Policies();
      });

      // init email templates tool

      this.tool("email_templates", ()=> {
        return new $peerctl.EmailTemplates();
      });

      // init device templates tool

      this.tool("device_templates", ()=> {
        return new $peerctl.DeviceTemplates();
      });

      this.$t.peering_lists.activate();
      this.$t.sessions_summary.activate();
      this.$t.policies.activate();
      this.$t.email_templates.activate();
      this.$t.device_templates.activate();
      this.$t.networks.activate();

      this.port_settings = $('#port-settings');

      $(this.$c.toolbar.$e.button_port_settings).on("click", () => {
        new $peerctl.modals.PortSettings();
      });

      $('a[data-select-asn]').click(function(){
        window.location.href = "?asn="+$(this).data("select-asn");
      });
      $(this.$c.toolbar.$e.peer_filter).on("keydown", (ev)=>{
        if(ev.which == 13) {
          this.$t.sessions_summary.sync();
        }
      });

      $('#tab-peering-lists').on('show.bs.tab', () => {
        this.$t.peering_lists.sync_url(
          this.port()
        );
      });

      $('#tab-summary-sessions').on('show.bs.tab', () => {
        this.$t.sessions_summary.sync_url(true);
      });

      $('#tab-ix').on('shown.bs.tab', () => {
        this.$t.ix.sync();
      });

      this.autoload_page();

    },

    permission_ui : function() {
      let $e = this.$c.toolbar.$e;
      let port = this.ports[this.port()];
      let org = $ctl.org.id;
    },

    port : function() {
      return this.$t.peering_lists.$w.select_port.element.val();
    },

    port_object: function() {
      return this.$t.peering_lists.ports[this.port()]
    },

    unload_port : function(id) {
      delete this.$t.peering_lists.ports[id];
      delete this.urlkeys[id];
      delete this.port_slugs[id];
    },

    sync_except: function(tool) {
      var i, app = this;
      for(i in this.$t) {
        if(this.$t[i].active && this.$t[i] != tool) {
          this.$t[i].sync();
        }
      }
    },

    refresh : function() {
      return this.refresh_select_port();
    },

    refresh_select_port : function() {
      return this.$t.peering_lists.$w.select_port.refresh();
    },

    /**
     * Parses the autoload parameters to determien whether
     * or not autloading is enabled for the provided page.
     *
     * Will also parse arguments into named attribtes and return
     * them in an object literal.
     *
     * TODO: move to fullctl/fullctl
     * @method autoload_enabled
     * @param {String} page page/tab name
     * @param {Function} validate_arg function to validate argument values
     * @param {Array} names attribute names
     */

    autoload_enabled : function(page, validate_arg, names) {
      if(!this.autoload_args || this.autoload_args[0] != page) {
        return null;
      }

      var valid = false;
      var arg, autoload = {}

      for(var i = 1; i < this.autoload_args.length; i++) {
        arg = this.autoload_arg(i);
        if(validate_arg(arg,i)) {
          valid = true;
          autoload[names[i-1]] = arg;
        }
      }
      if(!valid)
        return null;
      return autoload;
    }

  },
  $ctl.application.Application
);

$peerctl.NetworkSettings = $tc.extend(
  "NetworkSettings",
  {

    NetworkSettings : function() {
      this.Tool("network_settings");
    },

    init : function() {

      // write form

      this.widget("form", ($e) => {
        return new twentyc.rest.Form(
          this.template("form", this.$e.network_settings_container)
        );
      });


      // facilities list

      this.widget("facilities", ($e) => {
        return new twentyc.rest.List(
          this.template("facilities_list", this.$e.facilities_container)
        );
      });

      // exchanges list

      this.widget("exchanges", ($e) => {
        return new twentyc.rest.List(
          this.template("exchanges_list", this.$e.internet_exchanges_container)
        );
      });


      this.$w.form.wire_submit(this.$w.form.element.find('[data-element=save_network]'));

      this.button_update_peeringdb = this.$w.form.element.find('[data-element=export_network]');
      this.button_update_peeringdb.on("click", () => {
        var data = this.$w.form.payload();
        var dataDict = {
          "irr_as_set": data["as_set_override"] || data["as_set_peeringdb"],
          "info_prefixes4": data["prefix4_override"] || data["prefix4_peeringdb"],
          "info_prefixes6": data["prefix6_override"] || data["prefix6_peeringdb"],
          "info_type": data["network_type_override"] || data["network_type_peeringdb"],
          "info_ratio": data["ratio_override"] || data["ratio_peeringdb"],
          "info_traffic": data["traffic_override"] || data["traffic_peeringdb"],
          "info_scope": data["scope_override"] || data["scope_peeringdb"],
          "info_unicast": data["unicast_override"] || data["unicast_peeringdb"] === "Yes",
          "info_multicast": data["multicast_override"] || data["multicast_peeringdb"] === "Yes",
          "info_never_via_route_servers": data["never_via_route_servers_override"] || data["never_via_route_servers_peeringdb"] === "Yes",
        };
        // Redirect user to PeeringDB update verification page
        window.location.href = this.button_update_peeringdb.data('target')+"?source=peerCtl&"+$.param(dataDict);
      });

      // wire network type select input

      this.select_net_type = new twentyc.rest.Select(
        this.$w.form.element.find('[data-element=select_net_type]')
      )

      // wire network ratio select input

      this.select_ratio = new twentyc.rest.Select(
        this.$w.form.element.find('[data-element=select_ratio]')
      )

      // wire network traffic select input

      this.select_traffic = new twentyc.rest.Select(
        this.$w.form.element.find('[data-element=select_traffic]')
      )

      // wire network scope select input

      this.select_scope = new twentyc.rest.Select(
        this.$w.form.element.find('[data-element=select_scope]')
      )

      // normal selects

      this.select_multicast = this.$w.form.element.find('[data-element=select_multicast]');
      this.select_unicast = this.$w.form.element.find('[data-element=select_unicast]');
      this.select_never_via_route_servers = this.$w.form.element.find('[data-element=select_never_via_route_servers]');

      // load values into form

      this.sync();

      $(this.$w.form).on("api-write:success", (e, x, data)=> {
        this.sync_ux(data)
      });

      this.$w.form.element.find('.input-group .form-control').on("change", ()=>{
        this.sync_ux();
      });

      this.$w.form.element.find('.input-group .peeringdb-pull').on("click", function() {
        var input = $(this).siblings('.form-control');
        input.val("");
        input.trigger("change");
      });

      this.$w.form.element.find('.peeringdb-reset').on("click", ()=> {
        this.$w.form.element.find('.input-group .peeringdb-pull').trigger("click");
      });


    },

    sync_ux : function() {
      var comp = this;
      var fields_diff = [];
      this.$w.form.element.find('.input-group .form-control').each(function() {
        var name = $(this).attr("name");
        var value = $(this).val();
        if(value == "true")
          value = "Yes";
        if(value == "false")
          value = "No";
        var pdb_name = name.replace("_override", "_peeringdb");
        var pdb_value = $('[name='+pdb_name+']').val();
        //console.log($(this).val(), name, pdb_name, value, pdb_value);
        if(value === "" || value === null) {
          // peerctl override not set
          $(this).siblings('.peeringdb-pull').hide();
        } else {
          // peerctl override set
          if(value != pdb_value){
            $(this).siblings('.peeringdb-pull').show();
            fields_diff.push(name);
          } else {
            $(this).siblings('.peeringdb-pull').hide();
          }
        }
      });

      if(fields_diff.length) {
        $('.peeringdb-reset').show();
      } else {
        $('.peeringdb-reset').hide();
      }

    },


    /**
     * syncs the network form from the server
     * will retrieve network data and fill in the form
     * @method sync
     */

    sync : function() {

      this.$w.form.get("").then((response) => {
        var net = response.first();
        this.$w.form.fill(net);
        this.select_net_type.load(net.network_type_override).then(()=>{this.sync_ux()});
        this.select_ratio.load(net.ratio_override).then(()=>{this.sync_ux()});
        this.select_traffic.load(net.traffic_override).then(()=>{this.sync_ux()});
        this.select_scope.load(net.scope_override).then(()=>{this.sync_ux()});
        this.select_multicast.val(net.multicast_override === null ? "" : (net.multicast_override ? "true" : "false"));
        this.select_unicast.val(net.unicast_override === null ? "" : (net.unicast_override ? "true" : "false"));
        this.select_never_via_route_servers.val(net.never_via_route_servers_override === null ? "" : (net.never_via_route_servers_override ? "true" : "false"));
        this.sync_ux();
      });

      this.$w.facilities.load();
      this.$w.exchanges.load();

    }
  },
  $ctl.application.Tool
)

/**
 * Renders a list of exchanges for the selected ASN
 * @class Ix
 * @extends $ctl.application.Tool
 * @constructor
 * @namespace fullctl.peerctl
 */
$peerctl.Ix = $tc.extend(
  "Ix",
  {
    Ix: function() {
      this.Tool("ix");

      // init list

      this.widget("list", ($e) => {
        return new twentyc.rest.List(
          this.template("ix_list", this.$e.body)
        );
      });

      var list = this.$w.list;

      this.$w.list.format_request_url = (url) => {
        return url +"?ixi=1&load_md5=1";
      }

      this.$w.list.formatters.row = (row, data) => {
        row.find(".ix-header").attr("data-ix-header", data.ref_ix_id);

        // wire up clicking the ip column to change to the peering lists
        // page and auto select the port

        row.find("[data-element=ips").click((e) => {
          fullctl.peerctl.$t.peering_lists.sync(data.id);
          fullctl.peerctl.page("page-peering-lists");
        }).css("cursor", "pointer");

        // set up local action handler for opening the edit modal

        row.find("[data-action=edit]").click((e) => {
          console.log("DATA", data);
          new $peerctl.ModalIxPort(data);
        });

      };

      // format speed

      this.$w.list.formatters.speed = fullctl.formatters.pretty_speed;

      // format md5 field to simply show whether its set or not
      // instead of the actual md5 value

      this.$w.list.formatters.md5 =  fullctl.formatters.yesno;

      // format is_route_server_peer to show a checkmark if true

      this.$w.list.formatters.is_route_server_peer = fullctl.formatters.yesno;

      // render peeringdb or ixctl logo depending on ref_source value

      this.$w.list.formatters.ref_source = (value, data) => {
        if(value == "ixctl") {
          return $("<span>").addClass("fullctl-sot");
        }
        return "";
      };
      
      $(this.$w.list).on("load:after", () => {
        // only show first data-ix-header element distinguishing
        // by value of data-ix-header

        var shown = {};

        this.$w.list.element.find("[data-ix-header]").each(function() {
          var ix_id = $(this).data("ix-header");
          if(!shown[ix_id]) {
            $(this).show();
            shown[ix_id] = true;
          }
        });
      })
    },

    /**
     * Reloads the ix port list from the server
     * @method sync
     * @param {boolean} force - if true will force a reload from the server, otherwise respect a 60 second cache
     */

    sync: function(force) {
      
      // if force is false check if we have already loaded the list
      // in the last minute and dont sync if we have
      var now = new Date();

      if(!force) {
        var last_sync = this.$w.list.element.data("last-sync");
        if(last_sync) {
          var diff = now - last_sync;
          if(diff < 60000) {
            return;
          }
        }
      }

      // set last sync time
      this.$w.list.element.data("last-sync", now);
      
      this.$w.list.load();
    }
  },
  $ctl.application.Tool
)

/**
 * Modal that lets user edit the following values on an ixi port
 * 
 * - prefix4
 * - prefix6
 * - mac_address
 * - md5
 * 
 * @class ModalIxPort
 * @extends $ctl.application.Modal
 * @constructor
 * @param {object} port - the port object to edit
 * @namespace fullctl.peerctl
 */

$peerctl.ModalIxPort = $tc.extend(
  "ModalIxPort",
  {
    ModalIxPort: function(port) {
      var modal = this;
      var title = "Edit exchange port"
      var form = this.form = new twentyc.rest.Form(
        $ctl.template("form_ix_port")
      );

      // form api url needs to replace `pk` with port id
      form.format_request_url = (url) => {
        return url.replace("/0/", "/"+port.id+"/");
      }
      
      // fill form
      form.fill(port);

      // form success handler
      $(this.form).on("api-write:success", (ev, e, payload, response) => {
        modal.hide();
        fullctl.peerctl.$t.ix.$w.list.load();
      });

      // set up modal
      this.Modal("save_right", title, form.element);

      // wire form to submit
      form.wire_submit(this.$e.button_submit);
    }
  },
  $ctl.application.Modal
);
        

$peerctl.Networks = $tc.extend(
  "Networks",
  {

    Networks : function() {
      this.Tool("networks");
    },

    init : function() {
      this.widget("list", ($e) => {
        return new twentyc.rest.List(
          this.template("list", this.$e.body)
        );
      })

      this.$w.list.format_request_url = (url) => {
        return url.replace(/other_asn/, this.select_network_search.val());
      }

      $(this.$w.list).on("api-read:success", (ev, endpoint, payload, response) => {

        if(!response.first()) {
          $('#network-search-result-name').text("");
          $('#network-search-result-asn').text("");
          this.peer = null;
          $('#searched-asn').text("");
          return;
        }

        this.peer = response.first();

        $('#network-search-result-name').text(this.peer.name);
        $('#network-search-result-asn').text(this.peer.asn);
        $('#searched-asn').text(this.peer.asn);
      });

      this.$w.list.formatters.row = (row, data) => {
        row.data("ix-id", data.ix_id);

        var cont_us = $('<div>');
        var cont_them = $('<div>');
        var cont_mutual = $('<div>');
        var session_icon = $('<img>').attr('src', fullctl.util.static('common/icons/Indicator/Check-Ind/Check.svg')).addClass("indicator").attr("title", "Peering session(s) configured")
        var loc,i, node;


        for(i=0; i< data.our_locations.length; i++) {
          loc = data.our_locations[i];
          $('<div class="compact-row">').data("ix-id", loc.ix_id).append(
            $('<input type="checkbox">')
          ).append(
            $('<span>').text(loc.ix_name)
          ).appendTo(cont_us);
        }

        for(i=0; i< data.their_locations.length; i++) {
          loc = data.their_locations[i];
          $('<div class="compact-row">').data("ix-id", loc.ix_id).append(
            $('<input type="checkbox">')
          ).append(
            $('<span>').text(loc.ix_name)
          ).appendTo(cont_them);
        }

        for(i=0; i< data.mutual_locations.length; i++) {
          loc = data.mutual_locations[i];
          node = $('<div class="compact-row field">').data("ix-id", loc.ix_id).append(
            $('<input type="checkbox">').attr("disabled", loc.session).css("visibility", (loc.session ? "hidden" : "visible"))
          ).append(
            $('<span>').text(loc.ix_name).addClass((loc.session ? "session-active" : ""))
          ).appendTo(cont_mutual);

          if(loc.session) {
            node.append(session_icon.clone());
          }
        }

        row.find('.our-locations').append(cont_us);
        row.find('.their-locations').append(cont_them);
        row.find('.mutual-locations').append(cont_mutual);

      }

      $(this.$w.list).on("load:after", (ev,response) => {
        let request_peering = this.$w.list.element.find('[data-element=request_peering]');
        request_peering.show().prop("disabled", false).children('.label').hide().filter('.ok').show();

        let request_peering_tr = this.$w.list.element.find('[data-element=request_peering_tr]');

        this.$w.list.element.find('input[type=checkbox]').on("change", (ev) => {
          if(this.get_number_of_selected_networks() > 0) {
            request_peering.show().prop("disabled", false)
            request_peering_tr.show();
          } else {
            request_peering.show().prop("disabled", true)
            request_peering_tr.hide();
          }
        });

      });

      this.select_network_search = $ctl.peerctl.$c.toolbar.$e.network_search_asn;

      this.select_network_search.select2({
        ajax: {
          url : '/autocomplete/pdb/net',
          dataType: 'json',
          processResults : function(data, params) {

            var term = params.term;
            if(!isNaN(parseInt(term))) {
              var exact_found = data.results.find((obj) => { return obj.id == parseInt(term) });
              if(!exact_found) {
                data.results.unshift({
                  id: parseInt(term),
                  text: "AS"+term,
                  selected_text: "AS"+term
                });
              }
            }
            console.log("DATA", data.results, exact_found);
            return {
              results: data.results
            }
          }
        },
        placeholder: "Search by ASN"
      });

      this.select_network_search.on('select2:select', ()=> {
        this.sync();
      });

      $(document).on('select2:open', () => {
        document.querySelector('.select2-search__field').focus();
      });

      /*
      $(this.$w.list).on("load:after", () => {
        this.$e.request_peering.show();
      });

      this.input_network_search = $ctl.peerctl.$c.toolbar.$e.network_search;

      this.input_network_search.on("keydown", function(ev){
        if(ev.which == 13) {
          this.sync();
        }
      }.bind(this));

      this.btn_network_search = $ctl.peerctl.$c.toolbar.$e.network_search_submit;

      $(this.btn_network_search).click(function() {
        this.sync();
      }.bind(this));
      */

      this.$w.list.element.find("[data-element=request_peering]").on("click", () => {
        this.request_peering();
      });


    },

    sync : function() {
      if(this.select_network_search.val())
        this.$w.list.load();
    },

    get_number_of_selected_networks() {
      return this.$w.list.element.find('input[type=checkbox]:checked').length;
    },

    request_peering : function() {

      if(!this.peer) {
        return alert("No network in results");
      }

      var selected = this.$w.list.element.find('input[type=checkbox]:checked').parent()
      var ix_ids = []

      selected.each(function() {
        console.log(this);
        ix_ids.push($(this).data("ix-id"));
      });

      new $peerctl.modals.RequestPeeringFromAsn(
        this.peer,
        ix_ids,
      );

    }


  },
  $ctl.application.Tool
)

$peerctl.PeeringLists = $tc.extend(
  "PeeringLists",
  {
    PeeringLists : function() {
      this.Tool("peering_lists");

      this.ports = {};

      this.widget("select_port", ($e) => {
        let select_port = $('#page-peering-lists select[data-element="select_port"]');
        var w = new twentyc.rest.Select(select_port);
        $(w).on("load:after", (event, element, data) => {
          var i;
          for(i = 0; i < data.length; i++) {
            this.ports[data[i].id] = data[i];
          }
          if(data.length == 0) {
            select_port.attr('disabled', true);
          } else {
            select_port.attr('disabled', false)
          }
        });
        return w
      });

      this.widget("port_info", ($e) => {
        return $('#page-peering-lists [data-element="port_info"]');
      });

      this.widget("toggle_active_peers", ($e) => {
        return $('#page-peering-lists [data-element="toggle_active_peers"]');
      });

      this.widget("toggle_available_peers", ($e) => {
        return $('#page-peering-lists [data-element="toggle_available_peers"]');
      });

      this.$w.select_port.format_request_url = (url) => {
        return url + "?ixi=1";
      };


      $(this.$w.select_port).on("load:after", (e, select) => {
        this.$w.devicectl_device.load();
      });

      $(this.$w.devicectl_device).on("load:after", (e, select) => {
        let port_object = fullctl.peerctl.port_object();
        if(port_object)
          select.val(port_object.device.id);
        else
          select.val(select.find('option').first().val());
        this.$w.devicectl_port.device_id = select.val();
        if(this.$w.devicectl_port.device_id)
          this.$w.devicectl_port.load();
      });

      $(this.$w.select_port.element).on("change", () => {
        this.sync();
        this.sync_url(this.$w.select_port.element.val())
      });

      var peering_lists = this;
      this.$w.toggle_active_peers.click(function() {
        let button = $(this);
        let stat = peering_lists.$w.peers.toggle_active_peers();
        if(!stat)
          button.removeClass("fullctl").addClass("inactive");
        else
          button.addClass("fullctl").removeClass("inactive");
      });


      this.$w.toggle_available_peers.click(function() {
        let button = $(this);
        let stat = peering_lists.$w.peers.toggle_available_peers();
        if(!stat)
          button.removeClass("fullctl").addClass("inactive");
        else
          button.addClass("fullctl").removeClass("inactive");
      });

      this.sync();
    },

    init: function() {
      this.widget("peers", ($e) => {
        return new $peerctl.PeerList(this.template("peers", $e.body));
      });

      $(this.$w.peers).on("load:after", ()=>{
        this.$w.peers.update_counts();
      });

    },

    port : function() {
      return this.$w.select_port.element.val();
    },

    port_object: function() {
      return this.ports[this.port()]
    },

    sync_url: function(id) {
      window.history.pushState({}, '', "#page-peering-lists;"+id);
    },

    sync : function(port_id) {
      let port = this.port_object();
      this.$e.menu.find(".ixctl-controls").hide();

      // no port supplied to sync, get from select eleement
      if (!port_id) {
        port_id = (port?port.id:null);
      }

      // no port selected, get from autoload arguments
      if (!port_id) {
        if($ctl.peerctl.autoload_args) {
          if($ctl.peerctl.autoload_args[0] == "page-peering-lists") {
            port_id = $ctl.peerctl.autoload_args[1] || null;
            if(port_id == "null")
              port_id = null;
            this.sync_url(port_id);
          }
        }
      }

      this.$w.select_port.load(port_id).then(() => {
        let port = this.port_object();
        this.$w.port_info.find(".speed").text( $ctl.formatters.pretty_speed(port.speed) );
        this.$w.port_policy_4.element.val(port.policy4.id);
        this.$w.port_policy_6.element.val(port.policy6.id);
        this.$w.devicectl_device.element.val(port.device.id);
        this.$w.devicectl_port.element.val(port.id);

        this.$w.port_mac_address.element.val(port.mac_address);
        this.$w.port_is_route_server_peer.element.prop("checked", port.is_route_server_peer);
        //this.$w.net_as_set.element.val(fullctl.peerctl.network.as_set);

        this.$w.peers.load();
        this.$w.port_policy_4.load();
        this.$w.port_policy_6.load();
        this.$w.port_device_template.load();
      });
    },

    menu: function() {
      var menu = this.Tool_menu();

      this.widget("port_policy_4", ($e) => {
        return new $peerctl.PortPolicySelect(menu.find('[data-element="port_policy_4"]'), 4);
      })

      this.widget("port_policy_6", ($e) => {
        return new $peerctl.PortPolicySelect(menu.find('[data-element="port_policy_6"]'), 6);
      })

      this.widget("devicectl_device", ($e) => {
        return new $peerctl.DeviceSelect(menu.find('[data-element="devicectl_device"]'));
      });

      this.widget("devicectl_port", ($e) => {
        return new $peerctl.PortSelect(menu.find('[data-element="devicectl_port"]'));
      });

      this.widget("port_device_template", ($e) => {
        return new $peerctl.DeviceTemplateSelect(menu.find('[data-element="port_device_template"]'));
      });

      this.widget("port_mac_address", ($e) => {
        return new $peerctl.MacAddressInput(menu.find('[data-element="port_mac_address"]'));
      });

      this.widget("port_is_route_server_peer", ($e) => {
        return new $peerctl.IsRouteServerPeerInput(menu.find('[data-element="port_is_route_server_peer"]'));
      });

      /*

      this.widget("net_as_set", ($e) => {
        return new $peerctl.ASSetInput(menu.find('[data-element="net_as_set"]'));
      });

      */

      menu.find('[data-element="device_config"]').click(()=>{
        new $peerctl.modals.DeviceConfig();
      });


      $(this.$w.port_policy_4).on("load:after", (e, select, data) => {
        let port_object = fullctl.peerctl.port_object();
        if(port_object) {
          select.val(port_object.policy4.id);
        }
      });

      $(this.$w.port_policy_6).on("load:after", (e, select) => {
        let port_object = fullctl.peerctl.port_object();
        if(port_object)
          select.val(port_object.policy6.id);
      });

      var devicectl_port = this.$w.devicectl_port;

      $(this.$w.devicectl_device.element).on("change", function() {
        devicectl_port.device_id = $(this).val();
        devicectl_port.load();
        //this.$w.port_device_template.load();
      });

      $(this.$w.devicectl_port).on("load:after", (e, select) => {
        let port_object = fullctl.peerctl.port_object();
        if(port_object)
          select.val(port_object.id);
      });

      $(this.$w.devicectl_port).on("api-write:success", ()=>{
        this.sync(this.$w.devicectl_port.element.val());
        $ctl.peerctl.$t.sessions_summary.sync();
      });



      $(this.$w.port_mac_address).on("api-write:success", (ev, endpoint, sent_data, response)=>{
        //var data = response.first();
        //fullctl.peerctl.ports[data.id] = data;
      });

      /*
      $(this.$w.net_as_set).on("api-write:success", (ev, endpoint, sent_data, response)=>{
        var data = response.first();
        fullctl.peerctl.network.as_set = data.as_set;
      });
      */



      return menu;
    }
  },
  $ctl.application.Tool
);


$peerctl.Home = $tc.extend(
  "Home",
  {
    Home : function() {
      this.Tool("peering_home");
      this.widget("as_list", ($e) => {
        return $('.asn-container');
      });

      if(this.get_number_of_as() <= 1) {
        $ctl.peerctl.page("page-summary-sessions");
        $ctl.peerctl.hide_page("page-home");
      }
    },

    get_number_of_as : function() {
      return this.$w.as_list.find(".asn").length
    }

  },
  $ctl.application.Tool
);



$peerctl.SessionsSummary = $tc.extend(
  "SessionsSummary",
  {
    SessionsSummary : function() {
      this.Tool("peering_summary-sessions");

      this.ports = {};

      this.widget("select_port", ($e) => {
        return this.setup_select_filter('#page-summary-sessions select[data-element="select_port"]');
      });

      this.widget("select_device", ($e) => {
        return this.setup_select_filter('#page-summary-sessions select[data-element="select_device"]');
      });

      this.widget("select_facility", ($e) => {
        return this.setup_select_filter('#page-summary-sessions select[data-element="select_facility"]');
      });

      this.widget("btn_add_peer_session", ($e) => {
        return $('#page-summary-sessions button[data-element="btn_add_peer_session"]');
      });


      this.$w.select_port.format_request_url = (url) => {
        let device_filter = this.$w.select_device.element.val();
        if(device_filter != "all") {
          url = url + "?device="+device_filter;
        }
        return url;
      };

      this.$w.select_device.format_request_url = (url) => {
        return url.replace(/fac_tag/g, this.$w.select_facility.element.val());
      };

      $(this.$w.select_facility).one("load:after", () => {
        this.sync();
      });

      this.$w.btn_add_peer_session.click(() => {
        new $ctl.application.Peerctl.ModalFloatingSession(
          this.$w.select_facility.element.val(),
          this.$w.select_device.element.val(),
          this.$w.select_port.element.val(),
        );
      });

      // set up delete selected button
      this.delete_selected_button = this.$t.button_delete_selected;
      $(this.delete_selected_button).insertBefore(this.$w.btn_add_peer_session);

      // setup session summary widget
      this.widget("list_peer_sessions", ($e) => {
        let w = new $ctl.widget.SelectionList(
          $('#summary-sessions-body table'),
          $(this.delete_selected_button)
        );

        // handle policy editor widgets for each row
        w.formatters.row = (row, data) => {
          row.find("[data-action=edit_session]").click(() => {
            new $ctl.application.Peerctl.ModalFloatingSession(null, null, null, data);
          });

          if(data.status == "partial") {
            row.addClass("partial");
          }
        }

        w.formatters.meta4 = (value) => {
          if(!value)
            return "-";

          var node = $('<div>');
          node.append($('<span>').text(value.last_updown));
          node.append($('<button data-bs-html="true" data-bs-toggle="tooltip" data-bs-placement="top">').prop("title", fullctl.formatters.meta_data(value).html()).tooltip().append(
            $('<span class="icon fullctl icon-list">')
          ));

          return node;

        };

        w.formatters.meta6 = w.formatters.meta4;

        return w;
      });

      // set up delete select functionality
      $(this.delete_selected_button).click(() => {
        if (confirm("Remove selected Peer Sessions?")) {
          this.$w.list_peer_sessions.delete_selected_list();
        }
      });

      // determine autoloading of filter arguments

      var autoload = this.autoload = $ctl.peerctl.autoload_enabled(
        "page-summary-sessions",
        (v) => { return (v && v != "all"); },
        ["facility", "device", "port", "peer"]
      );

      // wire initial setting of filter values if autoload is enabled

      $(this.$w.select_facility).one("load:after", () => {
        if(autoload && autoload.facility) {
          this.$w.select_facility.element.val(autoload.facility);
          this.toggle_facility_filters();
        } else {
          this.sync();
        }
      });

      $(this.$w.select_device).one("load:after", () => {
        if(autoload && autoload.device) {
          this.$w.select_device.element.val(autoload.device);
          this.toggle_device_filters();
        }
      });

      $(this.$w.select_port).one("load:after", () => {
        if(autoload && autoload.port) {
          this.$w.select_port.element.val(autoload.port);
        }
      });

      $ctl.peerctl.$c.toolbar.$e.peer_filter.val(autoload ? autoload.peer : null);

      // wire triggering of sync if any filter values are changed

      $(this.$w.select_port.element).on("change", () => { this.sync();});
      $(this.$w.select_device.element).on("change", () => { this.toggle_device_filters(true); });
      $(this.$w.select_facility.element).on("change", () => { this.toggle_facility_filters(true); });

      // if autoloading of filters is enabled, sync the session list from
      // the filters provided in the autoload arguments

      if(autoload) {
        this.sync(
          autoload.facility,
          autoload.device,
          autoload.port,
          autoload.peer
        );
      }

      // always load values for the facility filter dropdown

      this.$w.select_facility.load();

    },

    /**
     * This will show the port filter if a device is selected
     * otherwise it will hide the port filter.
     *
     * @method toggle_device_filters
     * @param {bool} sync if true will sync the session list
     */

    toggle_device_filters : function(sync) {
      if(this.$w.select_device.element.val() == "all") {
        this.$w.select_port.element.parents('.toolbar-control-group').hide();
        this.$w.select_port.element.empty();
      } else {
        this.$w.select_port.element.parents('.toolbar-control-group').show();
        this.$w.select_port.element.empty();
        this.$w.select_port.load().then();
      }
      if(sync)
        this.sync();
    },

    /**
     * This will show the device filter if a facility is selected
     * otherwise it will hide the device and the port filter.
     *
     * @method toggle_facility_filters
     * @param {bool} sync if true will sync the session list
     */

    toggle_facility_filters : function(sync) {
      if(this.$w.select_facility.element.val() == "all") {
        this.$w.select_device.element.parents('.toolbar-control-group').hide();
        this.$w.select_port.element.parents('.toolbar-control-group').hide();
        this.$w.select_device.element.empty();
        this.$w.select_port.element.empty();
      } else {
        this.$w.select_device.element.parents('.toolbar-control-group').show();
        this.$w.select_port.element.parents('.toolbar-control-group').hide();
        this.$w.select_device.element.empty();
        this.$w.select_port.element.empty();
        this.$w.select_device.load();
      }

      if(sync)
        this.sync();
    },

    /**
     * Updates the # parameter in the url for autoloading
     *
     * filter arguments
     * @method sync_url
     * @param {Boolean} force if true will also update the url if the session summary is currently not visible
     * @param {String} facility facility slug
     * @param {Number} device device id
     * @param {Number} port port id
     * @param {String} q peer asn, name or ip
     */

    sync_url: function(force, facility, device, port, q) {
      if(this.$w.select_facility.element.is(":visible") || force) {
        window.history.pushState({}, '', "#page-summary-sessions;"+(facility||'')+";"+(device||'')+";"+(port||"")+";"+(q||""));
      }
    },

    /**
     * Syncs the session list from the api according to the specified
     * filter arguments
     *
     * If not filter arguments are provided, filters will be read from the
     * filter input elements.
     *
     * @method sync
     * @param {String} facility_filter facility slug
     * @param {Number} device_filter device id
     * @param {Number} port_filter port id
     * @param {String} peer_filter peer asn, name or ip
     */

    sync: function(facility_filter, device_filter, port_filter, peer_filter) {

      // if session summary is already syncing, do not start an additional
      // sync

      if(this.syncing)
        return;

      this.syncing = true;

      // if no filters were provided to the function read the filter values
      // from the various filter elements

      if(!facility_filter && !device_filter && !port_filter && !peer_filter) {
        port_filter = this.$w.select_port.element.val();
        device_filter = this.$w.select_device.element.val();
        facility_filter = this.$w.select_facility.element.val();
        peer_filter = $ctl.peerctl.$c.toolbar.$e.peer_filter.val();
      }

      if(peer_filter && !facility_filter) {
        facility_filter = "all";
      }

      this.$w.list_peer_sessions.action = "";

      // update the url with filter values

      this.sync_url(false, facility_filter, device_filter, port_filter, peer_filter);

      // build the request path from the filters

      var action = "";

      if(port_filter && !isNaN(port_filter)) {
        action = "port/"+port_filter;
      } else if(device_filter && !isNaN(device_filter)) {
        action = "device/"+device_filter;
      } else if(facility_filter != "all") {
        action = "facility/"+facility_filter;
      }

      this.$w.list_peer_sessions.payload = function() {
        if(peer_filter && peer_filter != "") {
          return {peer:peer_filter}
        }
        return {};
      }

      // update list

      this.$w.list_peer_sessions.action = action;
      this.$w.list_peer_sessions.load().finally(() => {this.syncing=false;});

      // update API view link

      this.$e.btn_api_view.attr("href", this.$w.list_peer_sessions.base_url+"/"+this.$w.list_peer_sessions.action);

    },

    setup_select_filter : function(selector) {
      let jq = $(selector);
      var w = new twentyc.rest.Select(jq);
      $(w).on("load:after", (event, element, data) => {
        var i;
        for(i = 0; i < data.length; i++) {
          this.ports[data[i].id] = data[i];
        }
        if(data.length == 0) {
          jq.attr('disabled', true);
        } else {
          jq.attr('disabled', false)
        }
      });
      return w
    },
  },
  $ctl.application.Tool
);


$ctl.application.Peerctl.ModalFloatingSession = $tc.extend(
  "ModalFloatingSession",
  {
    ModalFloatingSession : function(facility, device, port, session) {
      var modal = this;
      var title = "Add peer session"
      var form = this.form = new twentyc.rest.Form(
        $ctl.template("form_floating_session")
      );

      this.session = session;

      this.select_port = this.form.element.find('#port');
      this.select_policy_4 = new twentyc.rest.Select(this.form.element.find('#policy-4'));
      this.select_policy_6 = new twentyc.rest.Select(this.form.element.find('#policy-6'));

      if(port == "all")
        port = null;

      // setup port auto complete

      fullctl.ext.select2.init_autocomplete(

        // bind to port <select> element
        form.element.find("#port"),

        // parent dropdown to form element
        form.element,

        // options
        {

          // autocomplete url
          url: "/autocomplete/device/port?org="+fullctl.org.slug,

          // process results, allowing us to add entries for
          // ips that are not assigned to a port
          process: (data, term, params) => {
            if(fullctl.util.is_valid_ip4(term)) {

              // check if we have an exact match for the ip in the results
              var exact_found = data.results.find((obj) => { 
                return obj.text.primary && obj.text.primary.split("/")[0] == term
              });
    
              if(!exact_found) {

                // if no exact match was found, add an entry for the ip that
                // can be selected as a choice.

                data.results.unshift({
                  id: term,
                  text: {primary: term, secondary:"Ip not assigned", extra:""},
                  selected_text: {primary: term, secondary:"Ip not assigned", extra:""}
                });
              }
            }   
          },

          // place holder text for the search field
          placeholder: "Search IP, device, port or location names.",

          // if session is specifed, preselect it's port
          initial: (
            session ? 
            {
              id: session.port_id,
              primary: session.ip4, 
              secondary: session.port_interface, 
              extra: session.device_name
            } 
            : null
          )
        }
      );
    
      // edit existing session

      if(session) {
        title = "Edit Session ["+session.id+"]";
        form.fill(session);
        port = session.port_id;
      }

      this.preselect_port = port;

      this.select_policy_4.load(session ? session.policy4_id : null);
      this.select_policy_6.load(session ? session.policy6_id : null);

      $(this.form).on("api-write:success", (ev, e, payload, response) => {
        modal.hide();
        fullctl.peerctl.$t.sessions_summary.$w.list_peer_sessions.load();
      });

      this.Modal("save_right", title, form.element);
      form.wire_submit(this.$e.button_submit);
    }
  },
  $ctl.application.Modal
);

$peerctl.Policies = $tc.extend(
  "Policies",
  {
    Policies : function() {
      this.Tool("policies");
    },

    init: function() {
      this.widget("list", ($e) => {
        return new twentyc.rest.List(this.template("policy_list", $e.list_container));
      });

      this.widget("form", ($e) => {
        return new twentyc.rest.Form(this.template("form_policy", $e.editor));
      });

      this.edit_mode = false;
      this.active_changes = false;
      this.$w.list.local_actions.edit_policy = (policy)=>{
        this.$e.editor.removeClass("create");
        this.$w.form.form_action = policy.id;
        this.$w.form.method = "put";
        this.$w.form.fill(policy);
        this.$e.editor_title.text("Edit policy");
        this.edit_mode = true;
        this.$w.form.element.find(":input").on("input", (e) => {
          // might be out of edit mode when the listener fires
          if (this.edit_mode) {
            this.active_changes = true;
          }
        });
      };

      this.$w.list.formatters.row = (row, data) => {
        var global = []
        if(data.is_global4) {
          global.push("v4");
        }
        if(data.is_global6) {
          global.push("v6");
        }
        if(global.length) {
          row.find('[data-field="is_global"]').text("Global "+global.join(" "));
        }
      };


      this.$w.list.load();

      const reset_form = () => {
        this.$e.editor.addClass("create");
        this.$w.form.form_action = "";
        this.$w.form.method = "post";
        this.$w.form.reset();
        this.$e.editor_title.text("Create new policy");
        this.edit_mode = false;
      }

      this.$e.menu.find('[data-element="button_new_policy"]').click(()=>{
        if (this.edit_mode && this.active_changes &&
          !confirm("You have unsaved edits, are you sure you want to discard them?")) {
          return;
        }
        reset_form();
        this.$w.form.element.find(":input").first().focus();
      });

      this.$w.form.element.find('a.btn.btn-secondary').click(()=>{
        reset_form();
      });

      $(this.$w.form).on("api-write:success", ()=>{
        this.$w.list.load();
        if (!this.edit_mode) {
          reset_form();
        }
        this.active_changes = false;
        fullctl.peerctl.sync();
      });

    },

    sync : function() {
      this.$w.list.load();
    }
  },
  $ctl.application.Tool
);


$peerctl.TemplateEditor= $tc.extend(
  "TemplateEditor",
  {
    TemplateEditor : function() {
      this.Tool("email_templates");
      this.preview_timeout = new twentyc.util.SmartTimeout(()=>{},100);
    },

    init: function() {
      this.widget("list", ($e) => {
        return new twentyc.rest.List(this.template("template_list", $e.list_container));
      });

      this.widget("form", ($e) => {
        return new twentyc.rest.Form(this.template("form_template", $e.editor));
      });

      this.widget("select_type", ($e) => {
        return new twentyc.rest.Select(this.$w.form.element.find('#type'));
      });

      this.preview_client = new twentyc.rest.Client(
        this.$w.form.element.find("#preview").data("api-preview-default")
      );

      $(this.$w.select_type.element).on("change", ()=>{
        let val = this.$w.select_type.element.val();

        if(!val) {
          return this.$w.form.element.find('#preview,#body').val("")
        }

        $.ajax({
          method:'get',
          url:'/tmpl/'+this.tag+'/'+val
        }).done((text)=> {
          this.$w.form.element.find('#body').val(text);
          this.preview();
        });
      });

      this.edit_mode = false;
      this.active_changes = false;
      this.$w.list.local_actions.edit_template = (template)=>{
        this.$e.editor.removeClass("create");
        this.$w.form.form_action = template.id;
        this.$w.form.method = "put";
        this.$w.form.fill(template);
        this.$e.editor_title.text("Edit template");
        this.preview();
        this.edit_mode = true;
        this.$w.form.element.find(":input:not(#preview)").on("input", (e) => {
          // might be out of edit mode when the listener fires
          if (this.edit_mode) {
            this.active_changes = true;
          }
        });
      };

      this.$w.list.load();

      const reset_form = () => {
        this.$e.editor.addClass("create");
        this.$w.form.form_action = "";
        this.$w.form.method = "post";
        this.$w.form.reset();
        this.$e.editor_title.text("Create new template");
        this.$w.form.element.find('#preview,#body').val("");
        this.edit_mode = false;
      }

      this.$e.menu.find(`[data-element="button_new_${this.tag}"]`).click(()=>{
        if (this.edit_mode && this.active_changes &&
          !confirm("You have unsaved edits, are you sure you want to discard them?")) {
          return;
        }
        reset_form();
        this.$w.form.element.find(":input").first().focus();
      });

      this.$w.form.element.find('a.btn.btn-secondary').click(()=>{
        reset_form()
      });

      $(this.$w.form).on("api-write:success", ()=>{
        this.active_changes = false;
        if (!this.edit_mode) {
          reset_form();
        }
        this.$w.list.load();
      });
      this.$w.form.element.find("#body").on("input", ()=>{
        this.preview();
      });

    },

    sync : function() {
      this.$w.list.load();
    },

    preview : function() {
      var type =this.$w.select_type.element.val();
      this.$w.form.element.find('#preview').prop("disabled", true);
      this.preview_timeout.set(()=>{
        this.preview_client.post(null, {
          type: type,
          body: this.$w.form.payload().body,
          device: fullctl.peerctl.port_object().device.id
        }).then((response)=>{
          this.$w.form.element.find('#preview').
            val(response.first().body).
            prop("disabled", false);
        });
      },500);
    }
  },
  $ctl.application.Tool
);


$peerctl.EmailTemplates = $tc.extend(
  "EmailTemplates",
  {
    EmailTemplates : function() {
      this.tag = "email_template";
      this.Tool("email_templates");
      this.preview_timeout = new twentyc.util.SmartTimeout(()=>{},100);
    }
  },
  $peerctl.TemplateEditor
);

$peerctl.DeviceTemplates = $tc.extend(
  "DeviceTemplates",
  {
    DeviceTemplates : function() {
      this.tag = "device_template";
      this.Tool("device_templates");
      this.preview_timeout = new twentyc.util.SmartTimeout(()=>{},100);
    }
  },
  $peerctl.TemplateEditor
);




$peerctl.DeviceTemplateSelect = $tc.extend(
  "DeviceTemplateSelect",
  {
    load_params : function() {
      let port = fullctl.peerctl.port_object();
      if(port && port.device.type) {
        return {device_type: port.device.type};
      }
    }
  },
  twentyc.rest.Select
)

$peerctl.EmailTemplateSelect = $tc.extend(
  "EmailTemplateSelect",
  {
    load_params : function() {
    }
  },
  twentyc.rest.Select
)



$peerctl.PortPolicySelect = $tc.extend(
  "PortPolicySelect",
  {
    PortPolicySelect : function(jq, ip_version) {
      this.Select(jq);
      this.ip_version = ip_version;
    },
    payload : function() {
      return {
        value: this.element.val(),
        ipv: this.ip_version
      }
    },
    format_request_url: function(url,method) {
      if(method == "put") {
        url = this.element.data("api-action");
        return url.replace("/0/", "/"+ fullctl.peerctl.port() + "/");
      }
      return url;
    }
  },
  twentyc.rest.Select
)


$peerctl.PeerSessionPolicySelect = $tc.extend(
  "PeerSessionPolicySelect",
  {
    PeerSessionPolicySelect : function(jq, ip_version, port_id, peer_session_id) {
      this.PortPolicySelect(jq, ip_version);
      this.peer_session_id = peer_session_id;
      this.port_id = port_id;
    },
    payload : function() {
      return {
        value: this.element.val(),
        ipv: this.ip_version
      }
    },
    format_request_url: function(url,method) {
      if(method == "put") {
        url = this.element.data("api-action");
        return url.replace("port_id", this.port_id).replace("peer_session_id", this.peer_session_id);
      }
      return url;
    }
  },
  $peerctl.PortPolicySelect
)


$peerctl.PeerSessionToggle = $tc.extend(
  "PeerSessionToggle",
  {
    PeerSessionToggle: function(jq, peer_id, through_id, port_id, init_method) {
      this.Checkbox(jq);
      this.peer_id = peer_id;
      this.through_id = through_id;
      this.port_id = port_id;
      this.method = init_method;

      if (this.method.toUpperCase() == "DELETE") {
        jq.prop("checked", true);
        this.base_url = jq.data("api-base-togl");
      }

      $(this).on("api-write:success", ()=>{
        if (this.method.toUpperCase() == "POST") {
          this.method = "DELETE";
          this.base_url = jq.data("api-base-togl");
        } else {
          this.method = "POST";
          this.base_url = jq.data("api-base");
        }
      })
    },

    format_request_url: function(url, method) {
      var peer_session_id = this.element.data("peer_session-id")
      var port = (this.port_id || fullctl.peerctl.port())
      return url.replace("port_id", port).replace("peer_session_id", peer_session_id);
    },

    payload: function() {
      return {
        member: this.peer_id,
        through: this.through_id
      };

    },
  },
  twentyc.rest.Checkbox
);


$peerctl.DeviceSelect = $tc.extend(
  "DeviceSelect",
  {
    payload : function() {
      var port = fullctl.peerctl.port_object();
      port.device.type = this.element.val();
      return port.device
    },
    format_request_url: function(url,method) {
      if(method == "put") {
        url = url + "/" + this.element.data("api-action");
        return url.replace("/0/", "/"+ fullctl.peerctl.port_object().device.id + "/");
      }
      return url;
    }
  },
  twentyc.rest.Select
)

$peerctl.PortSelect = $tc.extend(
  "PortSelect",
  {
    format_request_url: function(url,method) {
      if(!fullctl.peerctl)
        return url;
      if(method == "put") {
        url = this.element.data("api-action");
      }
      if(method == "get") {
        url = url+"?device_id="+this.device_id
      }
      return url.replace("/0/", "/"+ fullctl.peerctl.port_object().id + "/");
    }
  },
  twentyc.rest.Select
)


$peerctl.MaxPrefixInput = $tc.extend(
  "MaxPrefixInput",
  {
    MaxPrefixInput : function(jq, peer_id) {
      this.Input(jq);
      this.ip_version = parseInt(jq.data("ip-version"));
      this.peer_id = peer_id;
    },
    format_request_url : function(url, method) {
      return url.replace("port_pk", fullctl.peerctl.port()).replace("peer_id", this.peer_id);
    },
    payload : function() {
      return {
        value: parseInt(this.element.val()),
        ipv: this.ip_version
      }
    }
  },
  twentyc.rest.Input
);

$peerctl.MacAddressInput = $tc.extend(
  "MacAddressInput",
  {
    format_request_url : function(url, method) {
      return url.replace("port_id", fullctl.peerctl.port());
    },
    payload : function() {
      return {
        mac_address: this.element.val()
      }
    }
  },
  twentyc.rest.Input
);

$peerctl.IsRouteServerPeerInput = $tc.extend(
  "IsRouteServerPeerInput",
  {
    format_request_url : function(url, method) {
      return url.replace("port_id", fullctl.peerctl.port());
    }
  },
  twentyc.rest.Checkbox
);


$peerctl.ASSetInput = $tc.extend(
  "ASSetInput",
  {
    payload : function() {
      return {
        value: this.element.val()
      }
    }
  },
  twentyc.rest.Input
);


$peerctl.PeerSessionList = $tc.extend(
  "PeerSessionList",
  {
    insert: function(data) {
      const list = this;
      const port_row = this.List_insert(data);
      const peer_row = this.peer_row;

      const init_method = data.peer_session_status == "ok" ? "delete" : "post";
      const switch_add = new $peerctl.PeerSessionToggle(
        port_row.find("input.peer_session-add"),
        data.id,
        data.origin_id,
        data.port_id,
        init_method
      );

      const button_show_config = port_row.find('button[data-element="peer_session_device_config"]');

      button_show_config.click(()=>{
        new $peerctl.modals.DeviceConfig(data);
      });


      $(switch_add).on("api-post:success", (ev, endpoint, sent_data, response)=>{
        port_row.addClass("peer_session-active").removeClass("peer_session-inactive");
        if(peer_row)
          peer_row.addClass("border-active").removeClass("border-inactive");
        list.fill_policy_selects(port_row, data);
        switch_add.element.data("peer_session-id", response.first().peer_session);
        fullctl.peerctl.$t.peering_lists.$w.peers.update_counts();
        fullctl.peerctl.sync_except(fullctl.peerctl.$t.peering_lists);
      });

      $(switch_add).on("api-delete:success", ()=>{
        port_row.addClass("peer_session-inactive").removeClass("peer_session-active");
        if(peer_row)
          peer_row.addClass("border-inactive").removeClass("border-active");
        fullctl.peerctl.$t.peering_lists.$w.peers.update_counts();
        fullctl.peerctl.sync_except(fullctl.peerctl.$t.peering_lists);
      });


      switch_add.element.data("peer_session-id", data.peer_session);

      if(data.peer_session_status == "ok") {
        port_row.addClass("peer_session-active").removeClass("peer_session-inactive");
        if(peer_row)
          peer_row.addClass("border-active").removeClass("border-inactive");
        list.fill_policy_selects(port_row, data);
      } else {
        port_row.addClass("peer_session-inactive").removeClass("peer_session-active");
        if(peer_row)
          peer_row.addClass("border-inactive").removeClass("border-active");
      }

    },

    fill_policy_selects : function(port_row, data) {
      new $peerctl.PeerSessionPolicySelect(
        port_row.find('.peer_session-policy-4'), 4, $ctl.peerctl.port(), data.peer_session
      ).element.val(data.policy4_id);

      new $peerctl.PeerSessionPolicySelect(
        port_row.find('.peer_session-policy-6'), 6, $ctl.peerctl.port(), data.peer_session
      ).element.val(data.policy6_id);

    }


  },
  twentyc.rest.List
);

$peerctl.MutualLocations = $tc.extend(
  "MutualLocations",
  {
    MutualLocations : function(jq, peer_id) {
      this.PeerSessionList(jq);
      this.peer_id = peer_id;
    },
    format_request_url : function(url, method) {
      return url.replace("port_id", fullctl.peerctl.port()).replace("peer_id", this.peer_id);
    }
  },
  $peerctl.PeerSessionList
);

$peerctl.PeerList = $tc.extend(
  "PeerList",
  {

    PeerList : function(jq) {
      this.List(jq);

      this.formatters.peeringdb = (value, data) => {

        const icon_col = $('<div>').addClass("col-auto").append(
          $('<span>').addClass("icon icon-launch icon-right")
        );
        const text_col = $('<div>').text("View on PDB").addClass("col label pe-0");
        const a_container = $('<div>').addClass("row align-items-center").append(text_col).append(icon_col)

        return $('<a>').attr('href', value).addClass("peer_session-active-toggled | secondary btn small ms-auto external").append(a_container);
      };
    },

    toggle_available_peers: function() {
      if(this.element.hasClass("hide-available-peers")) {
        this.element.removeClass("hide-available-peers");
        return true;
      } else {
        this.element.addClass("hide-available-peers");
        return false;
      }
    },


    toggle_active_peers: function() {
      if(this.element.hasClass("hide-active-peers")) {
        this.element.removeClass("hide-active-peers");
        return true;
      } else {
        this.element.addClass("hide-active-peers");
        return false;
      }
    },



    insert : function(data) {
      var row = this.List_insert(data);
      this.render_ports(row, data);


      row.find("button.toggle-mutual-locations").click(function() {
          var button = $(this);
          var container = row.find('.mutual-locations')

          var mutual_list = row.data("mutual-list");
          if(mutual_list) {
						button.find('.icon').removeClass('icon-caret-down').addClass('icon-caret-left');
            mutual_list.element.detach();
            row.data("mutual-list", null);
          } else {
            var loading = $ctl.loading_animation();
						button.find('.icon').addClass('icon-caret-down').removeClass('icon-caret-left');
            mutual_list = new $peerctl.MutualLocations(
              fullctl.template("port_list").data("data-api-base", button.data("data-api-base")),
              data.id
            );
            mutual_list.load();
            $(mutual_list).on("load:after", ()=>{ container.append(mutual_list.element); loading.detach(); });
            container.append(loading);
            row.data("mutual-list", mutual_list);
          }
      });


      new $peerctl.MaxPrefixInput(row.find('input[data-field="info_prefixes4"]'), data.id);
      new $peerctl.MaxPrefixInput(row.find('input[data-field="info_prefixes6"]'), data.id);

      row.find('[data-element="md5"]').click(()=>{
        new $peerctl.modals.MD5(data);
      });

      row.find('[data-element="request_peering"]').click(()=>{
        new $peerctl.modals.RequestPeering(data);
      });

      return row;
    },

    render_ports : function(row, data) {
      var list = this;
      var list_node = fullctl.template("port_list")
      var ports = new $peerctl.PeerSessionList(list_node);
      ports.peer_row = row;
      $(data.ipaddr).each(function() {
        this.ix_name = data.ix_name;
        this.device_id = data.device_id;
        var port_row = ports.insert(this);
      });


      row.find(".port-list").append(list_node)
      /* styles */
      const resize_observer = new ResizeObserver(entries => {
        for (let entry of entries) {
          row.find(".switch-col").outerWidth(entry.borderBoxSize[0].inlineSize);
        }
      });
      resize_observer.observe(row.find(".prefixes-col")[0])

      row.data("ports-widget", ports);

    },

    count_peers : function() {
      var active = 0;
      var available = 0;
      this.element.find('.peers-row').each(function() {
        if(!$(this).find('.peer_session-active').length)
          available += 1
        else
          active +=1
      });
      return [available, active]
    },

    update_counts : function() {
      var counts = this.count_peers();
      $(".port-info .active-peers").text(counts[1]);
      $(".port-info .available-peers").text(counts[0]);
    },

    format_request_url : function(url) {
      return url.replace("/0/", "/"+ fullctl.peerctl.port()+ "/");
    }
  },
  twentyc.rest.List
);




$peerctl.TemplatePreview = $tc.extend(
  "TemplatePreview",
  {
    TemplatePreview: function(jq, select_widget, type) {
      this.Form(jq);
      this.select = new select_widget(this.element.find('select'));
      this.editor = this.element.find('textarea');
      this.type = type;

      if(type) {
        this.select.filter = (tmpl) => {
          return tmpl.type == type;
        };
      }

      $(this.select).on("load:after", ()=>{ this.preview();});
      $(this.select.element).on("change", ()=>{ this.preview();});

      this.select.load();
    },

    preview_payload : function() {
      return { type: this.type }
    },

    preview : function() {
      var tmpl_id = parseInt(this.select.element.val())
      if(tmpl_id)
        var url = this.editor.data("api-preview").replace("tmpl_id", tmpl_id);
      else
        var url = this.editor.data("api-preview-default");
      var client = new twentyc.rest.Client(url);

      client.post(null, this.preview_payload()).then(
        (response)=>{
          this.editor.val(response.first().body);
        }
      );
    }
  },
  twentyc.rest.Form
);


$peerctl.EmailTemplatePreview = $tc.extend(
  "EmailTemplatePreview",
  {
    EmailTemplatePreview: function(jq, type, peer, ix_ids) {
      this.peer = peer;
      this.ix_ids = ix_ids;
      this.TemplatePreview(jq, $peerctl.EmailTemplateSelect, type);
    },

    preview_payload: function() {
      return {
        type: this.type,
        peer: this.peer.id,
        asn: this.peer.asn,
        ix_ids: this.ix_ids,
        peer_session: this.peer.peer_session
      }
    }
  },
  $peerctl.TemplatePreview
);


$peerctl.DeviceTemplatePreview = $tc.extend(
  "DeviceTemplatePreview",
  {
    DeviceTemplatePreview: function(jq, device, type, peer) {
      this.peer = peer;
      this.device = device;
      this.ConfigPreview(jq, $peerctl.DeviceTemplateSelect, type);
    },

    payload: function() {
      var payload = {
        type: this.type,
        device: this.device.id
      }

      if(this.peer) {
        payload.member = this.peer.id;
      }

      return payload;
    }
  },
  $ctl.ConfigPreview
);


$peerctl.modals = {};

$peerctl.modals.PortSettings = $tc.extend(
  "PortSettings",
  {

    PortSettings: function() {
      var port_settings = $ctl.peerctl.port_settings;
      var container = $('<div class="row">');
      container.append(port_settings);
      this.Modal("no_button", "Port settings", container);
      port_settings.show();
    }

  },
  $ctl.application.Modal
);

$peerctl.modals.MD5 = $tc.extend(
  "MD5",
  {
    MD5: function(peer) {
      this.peer = peer;
      var form = new twentyc.rest.Form(
        $ctl.template('form_md5')
      );
      form.fill(peer);
      form.format_request_url = (url) => {
        return url.replace("port_id", fullctl.peerctl.port()).replace("peer_id", peer.id);
      };

      $(form).on("api-write:success", (ev, endpoint, data)=>{
        this.hide();
        peer.md5 = data.md5;
      });


      this.Modal("save", peer.name, form.element);
      form.wire_submit(this.$e.button_submit);
    }
  },
  $ctl.application.Modal
);

$peerctl.modals.DeviceConfig = $tc.extend(
  "DeviceConfig",
  {
    DeviceConfig: function(peer) {
      this.peer = peer;
      var form = new $peerctl.DeviceTemplatePreview(
        $ctl.template('device_config'),
        peer ? {id:peer.device_id} : fullctl.peerctl.port_object().device,
        fullctl.peerctl.$t.peering_lists.$w.port_device_template.element.val(),
        peer
      );

      this.Modal("save_lg", "Device Config", form.element);
      this.$e.button_submit.text("Copy to clipboard").click(()=>{
        form.editor.select();
        document.execCommand("copy");
        this.hide();
      });
      //form.wire_submit(this.$e.button_submit);
    }
  },
  $ctl.application.Modal

);

$peerctl.modals.RequestPeering = $tc.extend(
  "RequestPeering",
  {
    RequestPeering: function(peer) {
      this.peer = peer;

      var current_step = "peer-request";
      var title = "Peering Request";

      if(peer.peer_session_status == "requested") {
        title = "Notify Configuration Complete";
        current_step = "peer-config-complete";
      } else if(peer.peer_session_status == "configured") {
        title = "Notify Peering Session Live";
        current_step = "peer-session-live";
      }

      var form = new $peerctl.EmailTemplatePreview(
        $ctl.template('form_request_peering'),
        current_step,
        peer
      );
      form.fill(peer);

      form.element.find('.'+current_step).addClass("highlight");


      form.format_request_url = (url) => {
        return url.replace("port_id", fullctl.peerctl.port()).replace("peer_id", peer.id);
      };
      $(form).on("api-write:success", (ev, endpoint, data, response)=>{

        if(form.element.find('#test-mode').is(":checked")) {
          console.log(response);
          alert("Test email has been sent");
          return;
        }

        this.hide();
        peer.peer_session_status = response.first().peer_session_status;
        peer.peer_session = response.first().peer_session;
        if(peer.peer_session_status == "ok") {
          fullctl.peerctl.$t.peering_lists.$w.peers.reload_row(peer.id)
        }
      });

      this.Modal("save_lg", title, form.element);
      form.wire_submit(this.$e.button_submit);

      this.$e.button_submit.empty().append($('<span>').addClass("icon icon-mail fullctl")).append($('<span>').addClass("label").text('Send'));
    }

  },
  $ctl.application.Modal
);


$peerctl.modals.RequestPeeringFromAsn = $tc.extend(
  "RequestPeeringFromAsn",
  {
    RequestPeeringFromAsn: function(peer, ix_ids) {

      var current_step = "peer-request";
      var title = "Peering Request";

      var form = new $peerctl.EmailTemplatePreview(
        $ctl.template('form_request_peering_from_asn'),
        current_step,
        peer,
        ix_ids
      );
      form.fill(peer);

      form.element.find('.'+current_step).addClass("highlight");

      $(form).on("api-write:success", (ev, endpoint, data, response)=>{

        if(form.element.find('#test-mode').is(":checked")) {
          console.log(response);
          alert("Test email has been sent");
          return;
        }

        this.hide();
      });

      this.Modal("save_lg", title, form.element);
      form.wire_submit(this.$e.button_submit);

      this.$e.button_submit.empty().append($('<span>').addClass("icon icon-mail fullctl")).append($('<span>').addClass("label").text('Send'));
    }

  },
  $ctl.application.Modal
);



$(document).ready(function() {
  $ctl.peerctl = new $peerctl();
});

})(jQuery, twentyc.cls, fullctl);
