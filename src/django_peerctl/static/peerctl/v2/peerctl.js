(function($, $tc, $ctl) {

var $peerctl = $ctl.application.Peerctl = $tc.extend(
  "Peerctl",
  {
    Peerctl: function() {
      this.Application("peerctl");

      if(!this.application_access_granted) {
        return;
      }

      // init home page tool
      this.tool("home", () => {
        return new $peerctl.Home();
      });

      // return if no asn selected
      if (!selected_asn) {
        return;
      }

      // init peering lists tool
      this.tool("peering_lists", () => {
        return new $peerctl.PeeringLists();
      });

      // init network settings tool
      this.tool("network_settings", () => {
        return new $peerctl.NetworkSettings();
      });

      // init ix tool
      this.tool("ix", () => {
        return new $peerctl.Ix();
      });


      // init policies management tool
      this.tool("policies", ()=> {
        return new $peerctl.Policies();
      });

      // init peering requests tool
      this.tool("peering_requests_list", ()=> {
        return new $peerctl.PeeringRequestsList();
      });

      const button_make_default = new twentyc.rest.Button(
        this.$c.header.$e.button_set_default_network
      );
      button_make_default.format_request_url = (url) => {
        return url.replace("network_asn", selected_asn);
      };
      $(button_make_default).on("api-write:success", (e, ev, d, response) => {
        alert("Default Network set successfully");
        if (!response.content.data[0]){
          return
        }

        const default_network = response.content.data[0].network
        this.$c.header.$e.select_network.find(`a[data-network-id="${default_network}"]`).append(
          this.$c.header.$e.default_network_label
        );
      });

      this.$t.peering_lists.activate();
      this.$t.peering_lists.sync_ports();
      this.$t.policies.activate();
      this.$t.peering_requests_list.activate();

      $($ctl).trigger("init_tools", [this]);

      this.port_settings = $('#port-settings');

      $(this.$c.toolbar.$e.button_port_settings).on("click", () => {
        new $peerctl.modals.PortSettings();
      });

      $('a[data-select-asn]').click(function(){
        window.location.href = "?asn=" + $(this).data("select-asn") + window.location.hash;
      });

      $('#tab-peering-lists').on('show.bs.tab', () => {
        this.$t.peering_lists.sync_url(
          this.port()
        );
      });

      // lazy loading of peering_lists
      $('#tab-peering-lists').one('show.bs.tab', () => {
        this.$t.peering_lists.sync()
      })

      $('#tab-ix').on('shown.bs.tab', () => {
        this.$t.ix.sync();
      });

      $('#tab-peering-requests').on('shown.bs.tab', () => {
        this.$t.peering_requests_list.sync();
      });

      this.autoload_page();

    },

    permission_ui : function() {
      let $e = this.$c.toolbar.$e;
      let port = this.ports[this.port()];
      let org = $ctl.org.id;
    },

    port : function() {
      return this.$t.peering_lists.$w.port_filter.element.val();
    },

    port_object : function() {
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
          new $peerctl.ModalIxPort(data);
        });

        if(data.ref_source == "ixctl"){
          row.addClass("ixctl-port");
          this.show_graph_controls(row, data)
        }

        row.attr("id", "ix-port-"+data.id);

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

        this.show_graphs();
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
    },

    // Function to indicate loading
    indicate_loading : function(row) {
      let graph_container = row.find("[data-element=graph_container]");
      console.log("LOADING GRAPH", graph_container.length, fullctl.template("graph_placeholder"))
      graph_container.empty().append(
        fullctl.template("graph_placeholder")
      );
      return this;
    },

    show_graph_controls(row, port) {
      fullctl.graphs.init_controls(row, this, (end_date, duration)=>{
        this.indicate_loading(row).show_graph(port, row, end_date, duration);
      });
      row.find('.graph-controls').show();
    },

    show_graphs : function() {
      this.$w.list.element.find("div.ixctl-port").each((i, row) => {
        row = $(row);
        let port = row.data("apiobject");
        this.indicate_loading(row);
        this.show_graph(port, row);
      });
    },

    // Function to show graphs
    show_graph : function(port, row, end_date, duration) {
      let graph_container = row.find("[data-element=graph_container]");

      if(!port.ref_id || port.ref_id.split(":")[0] != "ixctl") {
        graph_container.empty().append(message);
        return;
      }

      let url = this.$w.list.element.data('api-base') + "/" + port.id + "/traffic/ix";
      let params = [];
      if (end_date) {
        params.push('start_time=' + end_date);
      }
      if (end_date && duration) {
        params.push('duration=' + duration);
      }
      if (params.length > 0) {
        url += '?' + params.join('&');
      }

      console.log(port, "#ix-port-"+port.id+" .graph_container");

      fullctl.graphs.render_graph_from_file(
        url,
        "#ix-port-"+port.id+" .graph_container",
        port.virtual_port_name,
      ).then(() => {
        // check if a svg has been added to the container, if not, graph data was empty
        if(graph_container.find("svg").length == 0) {
          graph_container.empty().append(
            $('<div class="alert alert-info">').append(
              $('<p>').text("No traffic data available for this port.")
            )
          )
        } else {
          this.$e.refresh_traffic_graph.show();
        }
      })
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


$peerctl.PeeringLists = $tc.extend(
  "PeeringLists",
  {
    PeeringLists : function() {
      this.Tool("peering_lists");
      const peering_lists_tool = this;

      this.ports = {};

      this.widget("port_filter", ($e) => {
        return fullctl.ext.select2.init_autocomplete(

          // bind to port <select> element
          $('#page-peering-lists select#port-filter'),

          // parent dropdown to form element
          $('#page-peering-lists select#port-filter').parent(),

          // options
          {

            // autocomplete url
            url: '/autocomplete/device/ixi-port?asn=' + fullctl.peerctl.network.asn,

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
                    selected_text: {primary: term, secondary:"Ip not assigned", extra:""},
                  });
                }
              }
            },

            // place holder text for the search field
            placeholder: "Search IP, device, port or location names.",

            controls: false,

            localstorage_key: "peering_lists_port_filter"
          }
        );
      });
      const port_filter = this.$w.port_filter;
      this.$w.port_filter.load = (port_id) => {

        const list = this;
        // use data-api-ports to get a list of ports
        const port_api_url = this.$w.port_filter.element.data("api-ports");
        const select_element = this.$w.port_filter.element;

        return $.ajax({
          type: 'GET',
          dataType: 'json',
          url: port_api_url,
          // TODO: optimize response speed
          timeout: 30000,
          success: function(response){
            const data = response.data;
            for(let i = 0; i < data.length; i++) {
              peering_lists_tool.ports[data[i].id] = data[i];
            }

            // set value of select element on loading
            if (port_id) {
              if (select_element.find("option[value='" + port_id + "']").length)
                return
            } else {
              if (port_filter.localstorage_get() && peering_lists_tool.ports[port_filter.localstorage_get()])
                port_id = port_filter.localstorage_get();
              else
                port_id = Object.keys(peering_lists_tool.ports)[0];
            }
            if (!port_id) return;
            port_filter.localstorage_set(port_id);
            peering_lists_tool.sync_url(port_id);
            const port = peering_lists_tool.ports[port_id];
            let initial = {
              id: port.id,
              primary: port.ix_name,
              secondary: "",
              extra: ""
            };
            let option = $(new Option(initial.primary, initial.id, true, true));
            option.data("selection_data", initial);
            select_element.append(option);
            list.$w.devicectl_device.load();
          },
          fail: function(xhr, textStatus, errorThrown){
            console.log(xhr)
          }
        });
      };
      this.$w.port_filter.init_localstorage();

      this.$w.port_filter.element.on("change", () => {
        this.sync();
        this.sync_url(this.$w.port_filter.element.val())
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

      this.widget("searchbar", ($e) => {
        return new fullctl.application.Searchbar(
          $('#page-peering-lists [data-element="peer_searchbar"]'),
          () => this.sync(),
          () => this.sync()
        );
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
      return this.$w.port_filter.element.val();
    },

    port_object: function() {
      return this.ports[this.port()]
    },

    sync_url: function(id) {
      if (window.location.hash.indexOf("#page-peering-lists") == -1) {
        return
      }
      window.history.pushState({}, '', "#page-peering-lists;"+id);
    },

    sync : function(port_id) {
      const port = this.port_object();
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

      // Searchbar functionality
      const peer_filter = this.$w.searchbar.element.val();
      this.$w.peers.payload = () => {
        if(peer_filter && peer_filter != "") {
          return {peer:peer_filter}
        }
        return {};
      }

      // add loading shim to peers manually otherwise it will take a while
      // for it to appear as it needs to wait until the request resolves
      this.$w.peers.start_processing();

      this.$w.port_filter.load(port_id).then(() => {
        const port = this.port_object();
        if (!port) {
          this.$w.peers.done_processing();
          return;
        }
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

    sync_ports : function() {
      this.$w.port_filter.load()
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

      $(this.$w.list).on("api-write:success", ()=>{
        fullctl.peerctl.sync();
      });

    },

    sync : function() {
      this.$w.list.load();
    }
  },
  $ctl.application.Tool
);


$peerctl.PortPolicySelect = $tc.extend(
  "PortPolicySelect",
  {
    PortPolicySelect : function(jq, ip_version) {
      this.SimpleSelect2(jq, {dropdownParent: jq.parent()});
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
  fullctl.ext.SimpleSelect2
)


$peerctl.PeerSessionToggle = $tc.extend(
  "PeerSessionToggle",
  {
    PeerSessionToggle: function(jq, peer_port, peer, init_method) {
      this.Checkbox(jq);
      this.peer_id = peer_port.id;
      this.through_id = peer_port.origin_id;
      this.port_id = peer_port.port_id;
      this.peer = peer;
      this.peer_port = peer_port;
      this.mode = init_method;

      if (this.mode.toUpperCase() == "DELETE") {
        jq.prop("checked", true);
      }
    },

    format_request_url: function(url, method) {

      // if there is no session id then we need to POST to update_session
      // otherwise just replace port_id and peer_session_id
      const peer_session_id = this.element.data("peer_session-id")

      if(peer_session_id) {

        const port = (this.port_id || fullctl.peerctl.port())
        return url.replace("port_id", port).replace("peer_session_id", peer_session_id);

      } else {

        return fullctl.peerctl.$t.peering_lists.$w.peers.peer_sesion_update_url;

      }

    },

    payload: function() {
      let payload = {
        status : "ok",
        peer_asn: this.peer.asn,
        peer_ip4: this.peer_port.ipaddr4,
        peer_ip6: this.peer_port.ipaddr6,
        md5: this.peer.md5,
        peer_maxprefix4: this.peer.info_prefixes4,
        peer_maxprefix6: this.peer.info_prefixes6,
        peer_session_type: "ixi",
        port: Number($ctl.peerctl.port()),
      }

      if (this.mode.toUpperCase() == "DELETE") {
        payload.status = "configured";
      }

      return payload
    },

    render_non_field_errors: function(errors) {
      const error = errors[0];
      this.element.parent().after($('<div class="validation-error non-field-errors | text-nowrap position-absolute top-0 start-0">').text(error));
    },

    clear_errors : function() {
      this.element.parent().parent().find('.validation-error').detach();
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
    PeerSessionList: function(jq, peer_apiobject) {
      this.List(jq)
      this.peer = peer_apiobject;
    },

    insert: function(data) {
      const list = this;
      const port_row = this.List_insert(data);

      const switch_init_method = data.peer_session_status == "ok" ? "delete" : "post";
      const switch_add = new $peerctl.PeerSessionToggle(
        port_row.find("input.peer_session-add"),
        data,
        this.peer,
        switch_init_method
      );

      const button_show_config = port_row.find('button[data-element="peer_session_device_config"]');

      button_show_config.click(()=>{
        new $peerctl.modals.DeviceConfig(data);
      });


      const row = this.find_row(this.peer.id);
      $(switch_add).on("api-write:success", (ev, endpoint, sent_data, response) => {
        const loading_shim = fullctl.peerctl.$t.peering_lists.$w.peers.loading_shim;

        const offset_top = row.first().position().top;
        const offset_height = row.first().height();

        loading_shim.height(offset_height);
        loading_shim.css('top', offset_top);
        loading_shim.show();

        fullctl.peerctl.$t.peering_lists.$w.peers.reload_row(this.peer.id)
        .then(() => {
          fullctl.peerctl.$t.peering_lists.$w.peers.update_counts()
        })
        .finally(() => {
          loading_shim.height('');
          loading_shim.css('top', 0);
        });
        //fullctl.peerctl.sync_except(fullctl.peerctl.$t.peering_lists);
      });

      switch_add.element.data("peer_session-id", data.peer_session);

      list.fill_policy_selects(port_row, data);

    },

    /**
     * Fill policy selects and set the selected value to the policy id
     *
     * @method fill_policy_selects
     * @param {jQuery} port_row - The row of the port (jQuery object)
     * @param {Object} peer_session_apiobj - The peer session api object
     */

    fill_policy_selects : function(port_row, peer_session_apiobj) {

      // default policy id selection to 0, which will set it to "Inherit Policy"
      // this is true when we dont have a session yet, or when we have a session that
      // is specifically configured to inherit the policy

      var policy_4_id = 0;
      var policy_6_id = 0;

      // if we have a session that is not configured to inherit the policy, then
      // set the policy id to the policy id of the session


      if(peer_session_apiobj.policy4.id && !peer_session_apiobj.policy4.inherited) {
        policy_4_id = peer_session_apiobj.policy4.id;
      }

      if(peer_session_apiobj.policy6.id && !peer_session_apiobj.policy6.inherited) {
        policy_6_id = peer_session_apiobj.policy6.id;
      }

      // create the policy selects and set the selected value to the policy id

      new $peerctl.IPv4PeerSessionPolicySelect(
        port_row.find('.peer_session-policy-4'),
        $ctl.peerctl.port(),
        peer_session_apiobj,
        this.peer
      ).element.val(policy_4_id).trigger("change.select2");

      new $peerctl.IPv6PeerSessionPolicySelect(
        port_row.find('.peer_session-policy-6'),
        $ctl.peerctl.port(),
        peer_session_apiobj,
        this.peer
      ).element.val(policy_6_id).trigger("change.select2");

    }
  },
  twentyc.rest.List
);

$peerctl.PeerSessionPolicySelect = $tc.extend(
  "PeerSessionPolicySelect",
  {
    PeerSessionPolicySelect : function(jq, port_id, peer_session, peer) {
      this.SimpleSelect2(jq, {dropdownParent: jq.parent()});

      this.port_id = port_id;
      this.peer_session = peer_session;
      this.peer = peer;
      this.peer_session_id = peer_session.peer_session || null;


      $(this).on("api-write:success", (e, endpoint, data, response)=>{
        let session_data = response.first();
        let on_off_toggle = jq.closest('.list-body').find("input.peer_session-add");
        on_off_toggle.data('peer_session-id', session_data.id);
        this.peer_session_id = data.id;
      });
    },

    payload : function() {

      const payload = {
        peer_asn: this.peer.asn,
        peer_ip4: this.peer_session.ipaddr4,
        peer_ip6: this.peer_session.ipaddr6,
        port: Number(this.port_id),
        md5: this.peer.md5,
        peer_maxprefix4: this.peer.info_prefixes4,
        peer_maxprefix6: this.peer.info_prefixes6,
        peer_session_type: "ixi",
      }

      // if already has a peer session
      if (this.peer_session_id) {
        payload.id = this.peer_session.peer_session;
        payload.status = this.peer_session.status;
      } else {
        payload.status = "configured";
      }

      return payload;
    },

    format_request_url: function(url,method) {
      return fullctl.peerctl.$t.peering_lists.$w.peers.peer_sesion_update_url;
    }
  },
  fullctl.ext.SimpleSelect2
)

$peerctl.IPv4PeerSessionPolicySelect = $tc.extend(
  "IPv4PeerSessionPolicySelect",
  {
    IPv4PeerSessionPolicySelect : function(jq, port_id, peer_session, peer) {
      this.PeerSessionPolicySelect(jq, port_id, peer_session, peer);
    },

    payload : function() {
      const payload = this.PeerSessionPolicySelect_payload()
      payload.policy4 = Number(this.element.val());

      return payload;
    },
  },
  $peerctl.PeerSessionPolicySelect
);

$peerctl.IPv6PeerSessionPolicySelect = $tc.extend(
  "IPv6PeerSessionPolicySelect",
  {
    IPv6PeerSessionPolicySelect : function(jq, port_id, peer_session, peer) {
      this.PeerSessionPolicySelect(jq, port_id, peer_session, peer);
    },

    payload : function() {
      const payload = this.PeerSessionPolicySelect_payload()
      payload.policy6 = Number(this.element.val());

      return payload;
    },
  },
  $peerctl.PeerSessionPolicySelect
);


$peerctl.MutualLocations = $tc.extend(
  "MutualLocations",
  {
    MutualLocations : function(jq, peer_id, peer_apiobject) {
      this.PeerSessionList(jq, peer_apiobject);
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
      this.peer_sesion_update_url = this.element.data('api-update-url');

      this.formatters.peeringdb = (value, data) => {

        const icon_col = $('<div>').addClass("col-auto").append(
          $('<span>').addClass("icon icon-launch icon-right")
        );
        const text_col = $('<div>').text("View on PDB").addClass("col label pe-0");
        const a_container = $('<div>').addClass("row align-items-center").append(text_col).append(icon_col)

        return $('<a>').attr('href', value).addClass("peer_session-active-toggled | secondary btn small ms-auto external").append(a_container);
      };

      $(this).on("load:after", () => {
        let url = `/api/autopeer/${fullctl.peerctl.network.asn}/enabled/`

        $.ajax({
          url: url,
          method: "GET",
          headers : {
            "Content-Type" : "application/json",
            "X-CSRFToken" : twentyc.rest.config.csrf
          },
        }).then((response)=>{
          const autopeer_enabled_asns = {}
          response.data.forEach((asn)=>{
            autopeer_enabled_asns[asn.asn] = asn;
          });

          this.list_body.find(".peers-row").each(function() {
            const apiobject = $(this).data('apiobject')

            if(autopeer_enabled_asns[apiobject.asn] !== undefined) {
              const autopeer_data = autopeer_enabled_asns[apiobject.asn];
              const request_peering_btn = $(this).data('dropdown-peering-btn')

              // load function runs twice due to the structure of the List
              if (request_peering_btn.jq.find('button[data-element="request_peering_autopeering"]').length > 0)
                return;

              const autopeer_btn = $(`
                  <button
                    class="primary btn | small active"
                    data-option-text="Autopeer"
                    data-element="request_peering_autopeering"
                  >
                    <div class="row align-items-center">
                      <div class="col label pe-0">
                        Request peering
                      </div>
                      <div class="col-auto">
                        <span class="icon icon-api"></span>
                      </div>
                    </div>
                  </button>
              `)
              request_peering_btn.add_option(autopeer_btn);

              autopeer_btn.click(()=>{
                new $peerctl.modals.RequestPeering(
                  apiobject,
                  {
                    type: "autopeering",
                    url: autopeer_data.url,
                    autopeer_enabled: true,
                    asn: apiobject.asn
                  }
                );
              });

              $(this).find('[data-element="request_peering"]').off('click')
              $(this).find('[data-element="request_peering"]').on('click', ()=>{
                new $peerctl.modals.RequestPeering(
                  apiobject,
                  {
                    type: "email",
                    url: autopeer_data.url,
                    autopeer_enabled: true,
                    asn: apiobject.asn
                  }
                );
              });
            }
          })
        })
      })
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

      new $peerctl.OtherMutualLocationsButton(
        row.find("button.toggle-mutual-locations"),
        row,
        data
      );

      new $peerctl.MaxPrefixInput(row.find('input[data-field="info_prefixes4"]'), data.id);
      new $peerctl.MaxPrefixInput(row.find('input[data-field="info_prefixes6"]'), data.id);

      row.find('[data-element="md5"]').click(()=>{
        new $peerctl.modals.MD5(data);
      });


      row.find('[data-element="request_autopeering"]').click(()=>{
        let url = `/api/autopeer/${fullctl.peerctl.network.asn}/`
        let payload = {
          asn: data.asn,
        }

        $.ajax({
          url: url,
          method: "POST",
          data: JSON.stringify(payload),
          headers : {
            "Content-Type" : "application/json",
            "X-CSRFToken" : twentyc.rest.config.csrf
          },
        }).then((data)=>{
          console.log(data);
        });
      });

      row.find('[data-element="request_peering"]').click(()=>{
        new $peerctl.modals.RequestPeering(data);
      });

      const request_peering_btn = new fullctl.application.DropdownBtn(row.find('.dropdown-btn'));
      row.data('dropdown-peering-btn', request_peering_btn);

      return row;
    },

    render_ports : function(row, data) {
      const list_node = fullctl.template("port_list")
      const ports = new $peerctl.PeerSessionList(list_node, data);

      data.ipaddr.forEach((port) => {
        port.ix_name = data.ix_name;
        port.device_id = data.device_id;
        ports.insert(port);
      });

      const status = this.get_status(data);
      row.addClass(status);
      if (status == "complete") {
        row.find('[data-element="request_peering"]').hide();
      } else if (status == "incomplete") {
        row.find('[data-element="request_peering"] .label').text("Peering Requested");
      }

      if (this.is_peer_active(data)) {
        row.addClass('peers-active');
      } else {
        row.addClass('peers-inactive');
      }

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
      let available = 0;
      let active = 0;

      this.element.find('.peers-row').each(function() {
        if($(this).hasClass('peers-active'))
          active +=1
        else
          available += 1
      })

      return [available, active]
    },

    update_counts : function() {
      const counts = this.count_peers();
      $(".port-info .active-peers").text(counts[1]);
      $(".port-info .available-peers").text(counts[0]);
    },

    format_request_url : function(url) {
      return url.replace("/0/", "/"+ fullctl.peerctl.port()+ "/");
    },

    get_status : function(peer_data) {
      const status_counts = this.get_status_counts(peer_data);
      if (!status_counts)
        return;

      let status = "";
      if (status_counts["incomplete"] > 0) {
      // if any tasks are in progress
        status = "incomplete"
      } else if (status_counts["complete"] > 0 && status_counts["todo"] == 0) {
      // if all tasks are complete
        status = "complete"
      } else {
      // no incomplete tasks and some are todo
        status = "todo"
      }

      return status;
    },

    is_peer_active : function(peer_data) {
      const status_counts = this.get_status_counts(peer_data);
      if (!status_counts)
        return

      if (status_counts["complete"] > 0) {
        return true;
      }
      return false;
    },

    get_status_counts : function(peer_data) {
      if (peer_data.ipaddr.length == 0)
        return;

      const status_counts = {"complete": 0, "incomplete": 0, "todo": 0}

      peer_data.ipaddr.forEach((port) => {
        if (port.peer_session_status == "ok") {
          status_counts["complete"] += 1;
        } else if(port.peer_session_status != "ok" && peer_data.peer_request_status == "pending") {
          status_counts["incomplete"] += 1;
        } else {
          status_counts["todo"] += 1;
        }
      });

      return status_counts;
    }
  },
  twentyc.rest.List
);

$peerctl.OtherMutualLocationsButton = $tc.define(
  "OtherMutualLocationsButton",
  {
    OtherMutualLocationsButton : function(jq, row, data) {
      this.element = jq;
      this.row = row;
      this.data = data;

      const other_mutual_loc_count = data.mutual_locations_count - 1;
      if(other_mutual_loc_count > 0) {
        this.element.find('.icon').show();
        this.element.find('.text').text(`${other_mutual_loc_count} other exchange points`);
        this.element.click(this.toggle_mutual_list.bind(this));
      } else {
        this.element.find('.text').text("No other exchange points");
        this.element.find('.icon').hide();
        this.element.attr("disabled", true);
      }
    },

    toggle_mutual_list : function() {
      if(this.mutual_list) {
        this.remove_mutual_list();
      } else {
        this.add_mutual_list();
      }
    },

    remove_mutual_list : function() {
      this.element.find('.icon').removeClass('icon-caret-down').addClass('icon-caret-left');
      this.mutual_list.element.remove();
      this.mutual_list = null;
    },

    add_mutual_list : function() {
      const container = this.row.find('.mutual-locations')
      const loading = $ctl.loading_animation();

      this.element.find('.icon').addClass('icon-caret-down').removeClass('icon-caret-left');
      const mutual_list = this.mutual_list = new $peerctl.MutualLocations(
        fullctl.template("port_list").data("data-api-base", this.element.data("data-api-base")),
        this.data.id,
        this.data
      );
      $(mutual_list).on("load:after", ()=>{
        container.append(mutual_list.element);
        loading.remove();
      });
      mutual_list.load();
      container.append(loading);
    },
  }
)


$peerctl.TemplatePreview = $tc.extend(
  "TemplatePreview",
  {
    TemplatePreview : function(jq, select_widget, type) {
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

      var loading_shim = $('<div>').addClass("loading-shim")

      this.editor.parent().append(loading_shim);

      client.post(null, this.preview_payload()).then(
        (response)=>{
          loading_shim.detach();
          this.editor.val(response.first().body);
        },
        () => {
          loading_shim.detach();
        }
      );
    }
  },
  twentyc.rest.Form
);


$peerctl.EmailTemplatePreview = $tc.extend(
  "EmailTemplatePreview",
  {
    EmailTemplatePreview : function(jq, type, peer, ix_ids) {
      this.peer = peer;
      this.ix_ids = ix_ids;
      this.TemplatePreview(jq, $peerctl.EmailTemplateSelect, type);
    },

    payload : function() {
      let payload = this.TemplatePreview_payload();

      payload.ix_ids = this.ix_ids;

      return payload;
    },

    preview_payload : function() {
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
    DeviceConfig : function(peer) {
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
    RequestPeering : function(peer, request_data={type: "email"}, ix_ids) {
      this.peer = peer;
      this.request_data = request_data;
      this.ix_ids = ix_ids;

      let current_step = "peer-request";
      var title = "Peering Request";

      if(peer.peer_session_status == "requested") {
        title = "Notify Configuration Complete";
        current_step = "peer-config-complete";
      } else if(peer.peer_session_status == "configured") {
        title = "Notify Peering Session Live";
        current_step = "peer-session-live";
      }

      this.current_step = current_step;

      this.Modal("save_lg", title, $());

      this.change_peer_mode(request_data);
    },

    change_peer_mode : function(request_data) {
      const body_elements = [];
      if (request_data.autopeer_enabled) {
        const select_peer_method = this.select_peer_method = $(
          `<select class="form-select mb-4 mode-select">
            <option value="autopeering" selected>Autopeer</option>
            <option value="email">E-mail</option>
          </select>`
        );

        const modal = this;
        select_peer_method.on('change', function(ev) {
          const data = request_data;
          data.type = $(this).find('option:selected').val();
          modal.change_peer_mode(data);
        });

        // select the correct mode in dropdown
        this.select_peer_method.find(`[value="${request_data.type}"]`).attr('selected', true);
        body_elements.push(select_peer_method);
      }

      this.$e.button_submit.off('click')
      this.$e.button_submit.siblings('.autopeer-error').detach();

      // change body of modal based on mode
      if (request_data.type=="email") {
        const form = new $peerctl.EmailPeeringForm(this.current_step, this.peer, this.ix_ids);
        $(form).on("api-write:success", (ev, endpoint, data, response)=>{

          if(form.element.find('#test-mode').is(":checked")) {
            console.log(response);
            alert("Test email has been sent");
            return;
          }

          this.hide();
          this.peer.peer_session_status = response.first().peer_session_status;
          this.peer.peer_session = response.first().peer_session;
          fullctl.peerctl.$t.peering_lists.$w.peers.reload_row(this.peer.id)
          $(this).trigger("peer-request:after", []);
        });
        body_elements.push(form.element);
        this.$e.button_submit.empty().append($('<span>').addClass("icon icon-mail fullctl")).append($('<span>').addClass("label").text('Send'));
        form.wire_submit(this.$e.button_submit);
      } else if (request_data.type=="autopeering") {
        body_elements.push(
          new $peerctl.AutopeerModalBody(
            {
              peer_name: this.peer.name,
              asn: this.peer.asn,
              current_step: this.current_step,
              url: request_data.url
            }
          )
        );
        // wire submit button
        this.$e.button_submit.empty().append($('<span>').addClass("icon icon-api fullctl")).append($('<span>').addClass("label").text('Send'));
        this.$e.button_submit.on('click', (ev) => {
          const url = `/api/autopeer/${fullctl.peerctl.network.asn}/`
          const payload = {
            asn: this.peer.asn,
          }

          this.$e.button_submit.siblings('.autopeer-error').detach();

          $.ajax({
            url: url,
            method: "POST",
            data: JSON.stringify(payload),
            headers : {
              "Content-Type" : "application/json",
              "X-CSRFToken" : twentyc.rest.config.csrf
            },
          }).then((data)=>{
            console.log(data);
            this.hide();
            $(this).trigger("peer-request:after", []);
          }).fail((err)=>{
            // TODO: make prettier error response
            // all of this should really be in a twentyc.rest widget anyways
            let error_message = $('<div class="alert alert-danger autopeer-error">').text(err.responseJSON.errors)
            error_message.insertBefore(this.$e.button_submit);
          });
        });
      }

      this.set_content(body_elements);
    },

  },
  $ctl.application.Modal
);

$peerctl.EmailPeeringForm = $tc.define(
  "EmailPeeringForm",
  {
    EmailPeeringForm : function(current_step, peer, ix_ids) {
      const form = new $peerctl.EmailTemplatePreview(
        $ctl.template('form_request_peering'),
        current_step,
        peer,
        ix_ids
      );

      form.fill(peer);

      form.element.find('.'+current_step).addClass("highlight");

      form.format_request_url = (url) => {
        if (ix_ids) {
          return form.element.data('api-from-asn');
        }
        return url.replace("port_id", fullctl.peerctl.port()).replace("peer_id", peer.id);
      };

      if (ix_ids) {
        $(form).on("api-write:before", (ev, e, payload) => {
          payload["asn"] = peer.asn;
        });
      }

      return form
    }
  }
);

$peerctl.AutopeerModalBody = $tc.define(
  "AutopeerModalBody",
  {
    AutopeerModalBody: function(data) {
      this.element = $ctl.template('request_autopeer_body');
      this.element.find('.peer-name').text(data.peer_name);
      this.element.find('.peer-asn').text(data.asn);
      this.element.find('.'+data.current_step).addClass("highlight");
      this.element.find('a.autopeer-url').text(data.url).attr("href", data.url);

      return this.element;
    }
  }
)

$peerctl.ContinuePeerRequest = $tc.extend(
  "ContinuePeerRequest",
  {
    ContinuePeerRequest: function(jq, port_id) {
      this.Button(jq);
      this.port_id = port_id;
      this.method = "GET";

      $(this).on('api-read:success', (ev, endpoint, data, response)=> {
        let peer_info = response.first();
        let modal = new $peerctl.modals.RequestPeering(peer_info);
        $(modal).on("peer-request:after", (ev) => {
          $(this).trigger("peer-request:after", []);
        });

      });
    },

    format_request_url: function(url) {
      return url.replace("port_id", this.port_id);
    }

  },
  twentyc.rest.Button
)

$peerctl.PeeringRequestsList = $tc.extend(
  "PeeringRequestsList",
  {
    PeeringRequestsList : function() {
      this.Tool("peering_requests_list");

      this.ports = {};

      // setup session summary widget
      this.widget("list_peer_sessions", ($e) => {
        const w = new twentyc.rest.List(
          this.jquery.find('table'),
        );

        let peer_info_url = w.element.data('api-peer-info')

        w.format_request_url = () => {
          return `/api/autopeer/${fullctl.peerctl.network.asn}/`
        }

        w.formatters.status = (value, data) => {
          let bg_class;
          if(value == "completed")
            bg_class = "success";
          else if(value == "failed")
            bg_class = "danger";
          else if(value == "pending") {
            bg_class = "warning";

            if(data.type == "email" && data.peer_id && w.element.find('.row-'+data.id).length == 0) {
              let button_continue_element = $('<button class="badge badge-btn bg-primary action">').append(
                $('<span class="icon icon-mail">'),
                $('<span class="label">').text("continue")
              )
              let loading_indicator = $('<div class="loading-indicator-container fixed"><div class="loading-indicator"></div></div>').hide();

              button_continue_element.attr("data-api-base", peer_info_url).attr("data-api-action", data.peer_id);

              let button_continue = new $peerctl.ContinuePeerRequest(button_continue_element,data.port_id);
              $(button_continue).on('peer-request:after', () => { w.load();});

              let col = $('<div style="position:relative">').append(button_continue_element, loading_indicator);

              return col;
            }
          }

          return $("<div>").addClass("badge").addClass("bg-"+bg_class).text(value);
        }

        w.formatters.type = (value, data) => {
          let icon = "mail";
          let text = "Email"
          if(value == "autopeer") {
            icon = "api";
            text = "Autopeer";
          }

          const jq = $('<div class="d-flex justify-content-center align-items-center">');
          jq.append($(`<span class="icon icon-${icon} me-1" title="${value}">`))
          jq.append($("<span>").text(text))

          return jq;
        };

        w.formatters.date = fullctl.formatters.datetime;

        w.formatters.row = (row, data) => {
          // add network tooltip to asn
          const asn_field = row.find('[data-field="asn"]');
          asn_field.attr("data-bs-toggle", "tooltip")
            .attr("data-bs-placement", "top")
            .attr("title", data.name)
            .addClass("dotted-underline");
          new bootstrap.Tooltip(asn_field);

          // add view in summary functionality
          const view_in_summary_btn = row.find('[data-action="summary-button"]');
          view_in_summary_btn.on ('click', function() {
            fullctl.peerctl.page("page-summary-sessions");

            fullctl.peerctl.$t.sessions_summary.clear_select_filter();
            fullctl.peerctl.$t.sessions_summary.$w.searchbar.element.val(data.asn);
            fullctl.peerctl.$t.sessions_summary.$w.searchbar.search(data.asn);
          });
          if (data.sessions <= 0)
            view_in_summary_btn.hide();

          row.data("peering-request-id", data.id);
          if(data.num_locations > 1) {

            if(w.element.find('.row-'+data.id).length > 0) {
              // additional location of this request, hide it
              row.hide();
              row.addClass("secondary")
            } else {
              // first location of this request
              row.find("[data-field=location]").parent().addClass("action").click((ev) => {
                // toggle elements with the same .row-{data.id} class as this row
                // on or off, but this row should always remain visible
                w.element.find('.row-'+data.id).not(row).toggle();
              });
              row.find(".note-expand").show();
              row.find(".num-locations").text(data.num_locations-1);
            }
          }
          return row;
        };

        return w;
      });

      this.$e.refresh_peering_requests.click((ev) => { this.$w.list_peer_sessions.load(); });

      this.$w.list_peer_sessions.load();
    },

    sync: function() {
      this.$w.list_peer_sessions.load();
    }
  },
  $ctl.application.Tool
);


$(document).ready(function() {
  $ctl.peerctl = new $peerctl();
});

})(jQuery, twentyc.cls, fullctl);
