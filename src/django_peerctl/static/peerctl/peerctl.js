(function($, $tc, $ctl) {

var $peerctl = $ctl.application.Peerctl = $tc.extend(
  "Peerctl",
  {
    Peerctl: function() {
      this.Application("peerctl");

      this.ports = {}

      this.tool("peering_lists", () => {
        return new $peerctl.PeeringLists();
      });

      this.tool("policies", ()=> {
        return new $peerctl.Policies();
      });

      this.tool("email_templates", ()=> {
        return new $peerctl.EmailTemplates();
      });

      this.tool("device_templates", ()=> {
        return new $peerctl.DeviceTemplates();
      });




      this.$c.toolbar.widget("select_port", ($e) => {
        var w = new twentyc.rest.Select($e.select_port);
        $(w).on("load:after", (event, element, data) => {
          var i;
          for(i = 0; i < data.length; i++) {
            this.ports[data[i].id] = data[i];
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

      this.$c.toolbar.$e.toggle_active_peers.click(function() {
        let button = $(this);
        let stat = fullctl.peerctl.$t.peering_lists.$w.peers.toggle_active_peers();
        if(!stat)
          button.removeClass("fullctl").addClass("inactive");
        else
          button.addClass("fullctl").removeClass("inactive");
      });


      this.$c.toolbar.$e.toggle_available_peers.click(function() {
        let button = $(this);
        let stat = fullctl.peerctl.$t.peering_lists.$w.peers.toggle_available_peers();
        if(!stat)
          button.removeClass("fullctl").addClass("inactive");
        else
          button.addClass("fullctl").removeClass("inactive");
      });


      this.$t.peering_lists.activate();
      this.$t.policies.activate();
      this.$t.email_templates.activate();
      this.$t.device_templates.activate();

      $('a[data-select-asn]').click(function(){
        window.location.href = "?asn="+$(this).data("select-asn");
      });

    },


    permission_ui : function() {
      let $e = this.$c.toolbar.$e;
      let port = this.ports[this.port()];
      let org = $ctl.org.id;
    },

    port : function() {
      return this.$c.toolbar.$w.select_port.element.val();
    },

    port_object: function() {
      return this.ports[this.port()]
    },

    unload_port : function(id) {
      delete this.ports[id];
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
      var port = this.ports[id];
      var url = new URL(window.location)
      url.pathname = `/${fullctl.org.slug}`
      window.history.pushState({}, '', url);
    },

    sync : function() {
      let port = this.port_object();
      this.$t.peering_lists.$e.menu.find(".ixctl-controls").hide();

      if(!port) {
        return;
      }

      this.Application_sync();
      let port_info = this.$c.toolbar.$e.port_info
      port_info.find(".speed").text( $ctl.formatters.pretty_speed(port.speed) );
      this.$t.peering_lists.$w.port_policy_4.element.val(port.policy4.id);
      this.$t.peering_lists.$w.port_policy_6.element.val(port.policy6.id);
      this.$t.peering_lists.$w.port_device_type.element.val(port.device.type);

      if(port.ref_ix_id.indexOf("ixctl:") == 0) {
        this.$t.peering_lists.$e.menu.find(".ixctl-controls").show();
      }
      this.$t.peering_lists.$w.port_mac_address.element.val(port.mac_address);
      this.$t.peering_lists.$w.net_as_set.element.val(this.network.as_set);

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

$peerctl.PeeringLists = $tc.extend(
  "PeeringLists",
  {
    PeeringLists : function() {
      this.Tool("peering_lists");
    },

    init: function() {
      this.widget("peers", ($e) => {
        return new $peerctl.PeerList(this.template("peers", $e.body));
      });

      $(this.$w.peers).on("load:after", ()=>{
        this.$w.peers.update_counts();
      });

    },

    sync : function() {
      this.$w.peers.load();
      this.$w.port_policy_4.load();
      this.$w.port_policy_6.load();
      this.$w.port_device_template.load();
    },

    menu: function() {
      var menu = this.Tool_menu();
      this.widget("port_policy_4", ($e) => {
        return new $peerctl.PortPolicySelect(menu.find('[data-element="port_policy_4"]'), 4);
      })

      this.widget("port_policy_6", ($e) => {
        return new $peerctl.PortPolicySelect(menu.find('[data-element="port_policy_6"]'), 6);
      })

      this.widget("port_device_type", ($e) => {
        return new $peerctl.DeviceTypeSelect(menu.find('[data-element="port_device_type"]'));
      });


      this.widget("port_device_template", ($e) => {
        return new $peerctl.DeviceTemplateSelect(menu.find('[data-element="port_device_template"]'));
      });

      this.widget("port_mac_address", ($e) => {
        return new $peerctl.MacAddressInput(menu.find('[data-element="port_mac_address"]'));
      });

      this.widget("net_as_set", ($e) => {
        return new $peerctl.ASSetInput(menu.find('[data-element="net_as_set"]'));
      });

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

      $(this.$w.port_device_type).on("load:after", (e, select) => {
        let port_object = fullctl.peerctl.port_object();
        if(port_object)
          select.val(port_object.device.type);
      });

      $(this.$w.port_device_type).on("api-write:after", ()=>{
        this.$w.port_device_template.load();
      });

      $(this.$w.port_mac_address).on("api-write:success", (ev, endpoint, sent_data, response)=>{
        var data = response.first();
        fullctl.peerctl.ports[data.id] = data;
      });


      $(this.$w.net_as_set).on("api-write:success", (ev, endpoint, sent_data, response)=>{
        var data = response.first();
        fullctl.peerctl.network.as_set = data.as_set;
      });



      return menu;
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

      this.$w.list.local_actions.edit_policy = (policy)=>{
        this.$e.editor.removeClass("create");
        this.$w.form.form_action = policy.id;
        this.$w.form.method = "put";
        this.$w.form.fill(policy);
        this.$e.editor_title.text("Edit policy");
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

      this.$w.form.element.find('a.btn.btn-secondary').click(()=>{
        this.$e.editor.addClass("create");
        this.$w.form.form_action = "";
        this.$w.form.method = "post";
        this.$w.form.reset();
        this.$e.editor_title.text("Create new policy");
      });

      $(this.$w.form).on("api-write:success", ()=>{
        this.$w.list.load();
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

      this.$w.list.local_actions.edit_template = (template)=>{
        this.$e.editor.removeClass("create");
        this.$w.form.form_action = template.id;
        this.$w.form.method = "put";
        this.$w.form.fill(template);
        this.$e.editor_title.text("Edit template");
        this.preview();
      };

      this.$w.list.load();

      this.$w.form.element.find('a.btn.btn-secondary').click(()=>{
        this.$e.editor.addClass("create");
        this.$w.form.form_action = "";
        this.$w.form.method = "post";
        this.$w.form.reset();
        this.$e.editor_title.text("Create new template");
        this.$w.form.element.find('#preview,#body').val("");
      });

      $(this.$w.form).on("api-write:success", ()=>{
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
      this.tag = "emltmpl";
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
      this.tag = "devicetmpl";
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
  $peerctl.PortPolicySelect
)

$peerctl.PeerSessionButton = $tc.extend(
  "PeerSessionButton",
  {
    PeerSessionButton: function(jq, peer_id, through_id, port_id) {
      this.Button(jq);
      this.peer_id = peer_id;
      this.through_id = through_id;
      this.port_id = port_id;

    },
    format_request_url: function(url, method) {
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



$peerctl.DeviceTypeSelect = $tc.extend(
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
        value: this.element.val()
      }
    }
  },
  twentyc.rest.Input
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
      var list =this;
      var port_row = this.List_insert(data);
      var peer_row = this.peer_row;

        var button_add = new $peerctl.PeerSessionButton(
          port_row.find("button.peerses-add"),
          data.id,
          data.origin_id,
          data.port_id
        );


        var button_live = new $peerctl.PeerSessionButton(
          port_row.find("button.peerses-live"),
          data.id,
          data.origin_id,
          data.port_id
        );

        var button_show_config = port_row.find('button[data-element="peerses_device_config"]');

        button_show_config.click(()=>{
          new $peerctl.modals.DeviceConfig(data);
        });


        $(button_add).on("api-post:success", (ev, endpoint, sent_data, response)=>{
          port_row.addClass("peerses-active").removeClass("peerses-inactive");
          if(peer_row)
            peer_row.addClass("border-active").removeClass("border-inactive");
          list.fill_policy_selects(port_row, data);
          button_live.element.data("peerses-id", response.first().peerses);
          fullctl.peerctl.$t.peering_lists.$w.peers.update_counts();
        });

        $(button_live).on("api-delete:success", ()=>{
          port_row.addClass("peerses-inactive").removeClass("peerses-active");
          if(peer_row)
            peer_row.addClass("border-inactive").removeClass("border-active");
          fullctl.peerctl.$t.peering_lists.$w.peers.update_counts();
        });



        if(data.peerses_status == "ok") {
          button_live.element.data("peerses-id", data.peerses);
          port_row.addClass("peerses-active").removeClass("peerses-inactive");
          if(peer_row)
            peer_row.addClass("border-active").removeClass("border-inactive");
          list.fill_policy_selects(port_row, data);
        } else {
          port_row.addClass("peerses-inactive").removeClass("peerses-active");
          if(peer_row)
            peer_row.addClass("border-inactive").removeClass("border-active");
        }

    },
    fill_policy_selects : function(port_row, data) {
      new $peerctl.PeerSessionPolicySelect(
        port_row.find('.peerses-policy-4'), 4, data.peerses
      ).element.val(data.policy4.id);

      new $peerctl.PeerSessionPolicySelect(
        port_row.find('.peerses-policy-6'), 6, data.peerses
      ).element.val(data.policy6.id);

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
        var icon = $('<span>').addClass("icon icon-launch icon-right fullctl");
        var label = $('<span>').text("View on PeeringD");
        return $('<a>').attr('href', value).append(label).append(icon).addClass("external");
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
    EmailTemplatePreview: function(jq, type, peer) {
      this.peer = peer;
      this.TemplatePreview(jq, $peerctl.EmailTemplateSelect, type);
    },

    preview_payload: function() {
      return {
        type: this.type,
        peer: this.peer.id,
        peerses: this.peer.peerses
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
      this.TemplatePreview(jq, $peerctl.DeviceTemplateSelect, type);
    },

    preview_payload: function() {
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
  $peerctl.TemplatePreview
);


$peerctl.modals = {};

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

      if(peer.peerses_status == "requested") {
        title = "Notify Configuration Complete";
        current_step = "peer-config-complete";
      } else if(peer.peerses_status == "configured") {
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
        this.hide();
        peer.peerses_status = response.first().peerses_status;
        peer.peerses = response.first().peerses;
        if(peer.peerses_status == "ok") {
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



$(document).ready(function() {
  $ctl.peerctl = new $peerctl();
});

})(jQuery, twentyc.cls, fullctl);
