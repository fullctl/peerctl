(function($, $tc, $ctl) {

$ctl.application.Peerctl = $tc.extend(
  "Peerctl",
  {
    Peerctl: function() {
      this.Application("peerctl");

      this.exchanges = {}

      this.tool("peering_lists", () => {
        return new $ctl.application.Peerctl.PeeringLists();
      });


      this.$c.toolbar.widget("select_port", ($e) => {
        var w = new twentyc.rest.Select($e.select_port);
        $(w).on("load:after", (event, element, data) => {
          var i;
          for(i = 0; i < data.length; i++) {
            this.exchanges[data[i].id] = data[i];
          }
          if(data.length == 0) {
            $e.select_port.attr('disabled', true);
          } else {
            $e.select_port.attr('disabled', false)
          }
        });
        return w
      });

      this.$c.toolbar.widget("port_info", ($e) => {
        return $e.port_info;
      });


      $(this.$c.toolbar.$w.select_port).one("load:after", () => {
        if(this.preselect_port) {
          this.select_port(this.preselect_port)
        } else {
          this.sync();
          this.sync_url(this.$c.toolbar.$e.select_port.val());
        }
      });


      $(this.$c.toolbar.$e.select_port).on("change", () => {
        this.sync();
        this.sync_url(this.$c.toolbar.$e.select_port.val())
      });

      this.$t.peering_lists.activate();

    },


    permission_ui : function() {
      let $e = this.$c.toolbar.$e;
      let port = this.exchanges[this.port()];
      let org = $ctl.org.id;
    },

    port : function() {
      return this.$c.toolbar.$w.select_port.element.val();
    },

    port_object: function() {
      return this.exchanges[this.port()]
    },

    unload_port : function(id) {
      delete this.exchanges[id];
      delete this.urlkeys[id];
      delete this.port_slugs[id];
    },

    select_port : function(id) {
      if(id)
        this.$c.toolbar.$e.select_port.val(id);
      else
        this.$c.toolbar.$e.select_port.val(this.$c.toolbar.$e.select_port.find('option').val());

      this.sync();
      this.sync_url(id);
    },

    sync_url: function(id) {
			return;
      var port = this.exchanges[id];
      var url = new URL(window.location)
      url.pathname = `/${fullctl.org.slug}`
      window.history.pushState({}, '', url);
    },

    sync : function() {
      this.Application_sync();
      let port = this.port_object();
      let port_info = this.$c.toolbar.$e.port_info
      port_info.find(".speed").text(port.speed);
      this.$t.peering_lists.$w.port_policy_4.element.val(port.policy4.id);
      this.$t.peering_lists.$w.port_policy_6.element.val(port.policy6.id);
      this.$t.peering_lists.$w.port_device_type.element.val(port.device.type);

      this.$t.peering_lists.$w.port_device_template.load();
    },

    refresh : function() {
      return this.refresh_select_port();
    },

    refresh_select_port : function() {
      return this.$c.toolbar.$w.select_port.refresh();
    }

  },
  $ctl.application.Application
);

$ctl.application.Peerctl.DeviceTemplateSelect = $tc.extend(
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


$ctl.application.Peerctl.PortPolicySelect = $tc.extend(
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


$ctl.application.Peerctl.PeerSessionPolicySelect = $tc.extend(
  "PeerSessionPolicySelect",
  {
    PeerSessionPolicySelect : function(jq, ip_version, peerses_id) {
      this.PortPolicySelect(jq, ip_version);
      this.peerses_id = peerses_id;
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
        return url.replace("port_id", fullctl.peerctl.port()).replace("peerses_id", this.peerses_id);
      }
      return url;
    }
  },
  $ctl.application.Peerctl.PortPolicySelect
)

$ctl.application.Peerctl.PeerSessionButton = $tc.extend(
  "PeerSessionButton",
  {
    PeerSessionButton: function(jq, peer_id, through_id, port_id) {
      this.Button(jq);
      this.peer_id = peer_id;
      this.through_id = through_id;
      this.port_id = port_id;

    },
    format_request_url: function(url, method) {
      url = this.element.data("api-action");
      var peerses_id = this.element.data("peerses-id")

      var port = (this.port_id || fullctl.peerctl.port())

      return url.replace("port_id", port).replace("peerses_id", peerses_id);
    },
    payload: function() {
      return {
        member: this.peer_id,
        through: this.through_id
      };

    }
  },
  twentyc.rest.Button
);



$ctl.application.Peerctl.DeviceTypeSelect = $tc.extend(
  "DeviceTypeSelect",
  {
    payload : function() {
      var port = fullctl.peerctl.port_object();
      port.device.type = this.element.val();
      return port.device
    },
    format_request_url: function(url,method) {
      if(method == "put") {
        url = this.element.data("api-action");
        return url.replace("/0/", "/"+ fullctl.peerctl.port_object().device.id + "/");
      }
      return url;
    }
  },
  twentyc.rest.Select
)

$ctl.application.Peerctl.MaxPrefixInput = $tc.extend(
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

$ctl.application.Peerctl.PeerSessionList = $tc.extend(
  "PeerSessionList",
  {
    insert: function(data) {
      var list =this;
      var port_row = this.List_insert(data);
        var button_add = new $ctl.application.Peerctl.PeerSessionButton(
          port_row.find("button.peerses-add"),
          data.id,
          data.origin_id,
          data.port_id
        );


        var button_live = new $ctl.application.Peerctl.PeerSessionButton(
          port_row.find("button.peerses-live"),
          data.id,
          data.origin_id,
          data.port_id
        );


        $(button_add).on("api-post:success", (endpoint, peerses_data)=>{
          port_row.addClass("peerses-active").removeClass("peerses-inactive");
          list.fill_policy_selects(port_row, data);
          button_live.element.data("peerses-id", peerses_data.peerses);
          fullctl.peerctl.$t.peering_lists.$w.peers.update_counts();
        });

        $(button_live).on("api-delete:success", (endpoint, data)=>{
          port_row.addClass("peerses-inactive").removeClass("peerses-active");
          fullctl.peerctl.$t.peering_lists.$w.peers.update_counts();
        });



        if(data.peerses_status == "ok") {
          button_live.element.data("peerses-id", data.peerses);
          port_row.addClass("peerses-active").removeClass("peerses-inactive");
          list.fill_policy_selects(port_row, data);
        } else {
          port_row.addClass("peerses-inactive").removeClass("peerses-active");
        }

    },
    fill_policy_selects : function(port_row, data) {
      new $ctl.application.Peerctl.PeerSessionPolicySelect(
        port_row.find('.peerses-policy-4'), 4, data.peerses
      ).element.val(data.policy4.id);

      new $ctl.application.Peerctl.PeerSessionPolicySelect(
        port_row.find('.peerses-policy-6'), 6, data.peerses
      ).element.val(data.policy6.id);

    }


  },
  twentyc.rest.List
);

$ctl.application.Peerctl.MutualLocations = $tc.extend(
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
  $ctl.application.Peerctl.PeerSessionList
);

$ctl.application.Peerctl.PeerList = $tc.extend(
  "PeerList",
  {
    insert : function(data) {
      var row = this.List_insert(data);
      this.render_ports(row, data);


      row.find("button.toggle-mutual-locations").click(function() {
          var button = $(this);
          var container = row.find('.mutual-locations')

          var mutual_list = row.data("mutual-list");
          if(mutual_list) {
            mutual_list.element.detach();
            row.data("mutual-list", null);
          } else {
            mutual_list = new $ctl.application.Peerctl.MutualLocations(
              fullctl.template("port_list").data("data-api-base", button.data("data-api-base")),
              data.id
            );
            mutual_list.load();
            container.append(mutual_list.element);
            row.data("mutual-list", mutual_list);
          }
      });


      new $ctl.application.Peerctl.MaxPrefixInput(row.find('input[data-field="info_prefixes4"]'), data.id);
      new $ctl.application.Peerctl.MaxPrefixInput(row.find('input[data-field="info_prefixes6"]'), data.id);

      return row;
    },

    render_ports : function(row, data) {
      var list = this;
      var list_node = fullctl.template("port_list")
      var ports = new $ctl.application.Peerctl.PeerSessionList(list_node);
      $(data.ipaddr).each(function() {
        this.ix_name = data.ix_name;
        var port_row = ports.insert(this);
      });


      row.find(".port-list").append(list_node)

      row.data("ports-widget", ports);

    },

    count_peers : function() {
      var active = 0;
      var available = 0;
      this.element.find('.peers-row').each(function() {
        if(!$(this).find('.peerses-active').length)
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



$ctl.application.Peerctl.PeeringLists = $tc.extend(
  "PeeringLists",
  {
    PeeringLists : function() {
      this.Tool("peering_lists");
    },

    init: function() {
      this.widget("peers", ($e) => {
        return new $ctl.application.Peerctl.PeerList(this.template("peers", $e.body));
      });

      $(this.$w.peers).on("load:after", ()=>{
        this.$w.peers.update_counts();
      });
    },

    sync : function() {
      this.$w.peers.load();
    },

    menu: function() {
      var menu = this.Tool_menu();
      this.widget("port_policy_4", ($e) => {
        return new $ctl.application.Peerctl.PortPolicySelect(menu.find('[data-element="port_policy_4"]'), 4);
      })

      this.widget("port_policy_6", ($e) => {
        return new $ctl.application.Peerctl.PortPolicySelect(menu.find('[data-element="port_policy_6"]'), 6);
      })

      this.widget("port_device_type", ($e) => {
        return new $ctl.application.Peerctl.DeviceTypeSelect(menu.find('[data-element="port_device_type"]'));
      });


      this.widget("port_device_template", ($e) => {
        return new $ctl.application.Peerctl.DeviceTemplateSelect(menu.find('[data-element="port_device_template"]'));
      });

      $(this.$w.port_policy_4).on("load:after", (e, select, data) => {
        let port_object = fullctl.peerctl.port_object();
        if(port_object) {
          select.val(port_object.policy4.id);
        }
      });

      $(this.$w.port_policy_6).on("load:after", (e, select) => {
        let port_object = fullctl.peerctl.port_object();
        console.log("SELECT", select);
        if(port_object)
          select.val(port_object.policy6.id);
      });

      $(this.$w.port_device_type).on("load:after", (e, select) => {
        let port_object = fullctl.peerctl.port_object();
        if(port_object)
          select.val(port_object.device.type);
      });

      $(this.$w.port_device_type).on("api-write:after", ()=>{
        this.$w.port_device_template.load();
      });



      return menu;
    }
  },
  $ctl.application.Tool
);


$(document).ready(function() {
  $ctl.peerctl = new $ctl.application.Peerctl();
});

})(jQuery, twentyc.cls, fullctl);
