(window.webpackJsonp=window.webpackJsonp||[]).push([[42],{clPc:function(K,d,t){"use strict";t.r(d);var ne=t("T2oS"),b=t("W9HT"),x=t("+L6B"),O=t("2/Rp"),z=t("DYRE"),g=t("zeV3"),J=t("giR+"),D=t("fyUT"),F=t("7Kak"),u=t("9yH6"),j=t("k1fw"),$=t("miYZ"),I=t("tsqr"),B=t("9og8"),f=t("tJVT"),re=t("tU7J"),o=t("wFql"),le=t("jCWc"),S=t("kPKH"),be=t("14J3"),Z=t("BMrR"),y=t("qqnG"),h=t("WmNS"),a=t.n(h),n=t("q1tI"),e=t.n(n),i=t("Ty5D"),M=t("9kvl"),s=t("qTtT"),G=t("ZqBY"),je=function(m){return Object(G.a)("/api/sys/ws_config/",{params:m})},oe=function(m){return Object(G.a)("/api/sys/ws_config/",{method:"put",data:m})},Se=t("en/e"),A=t("vOnD"),Ze=t("+BJd"),p=t("mr32"),Me=t("jrin"),se,ue,Pe=Object(A.a)(Z.a)(se||(se=Object(y.a)([`
    margin-top:16px;
    &:first-child {
        margin-top:0px;
    }
`]))),Re=Object(A.a)(S.a)(ue||(ue=Object(y.a)([`
    text-align:right;
    &::after {
        content: '\uFF1A';
    }
`]))),xe=function(m){var W=m.title,P=m.children;return e.a.createElement(Pe,{gutter:20},e.a.createElement(Re,{span:4},W),e.a.createElement(S.a,{span:20},P))},Ae=Object(n.memo)(xe),Fe=function(m){var W=m.dataSource,P=m.update,Y=m.field,L=W[Y],_=function(k){var N=k.target;return P(Object(Me.a)({},Y,N.value))};return e.a.createElement(Ae,{title:"\u529F\u80FD\u6D4B\u8BD5\u7ED3\u679C\u7C7B\u578B"},e.a.createElement(u.a.Group,{defaultValue:L,onChange:_,value:L},e.a.createElement(u.a,{value:"1"},"type1"),e.a.createElement(u.a,{value:"2"},e.a.createElement(s.a,{title:"type2",desc:e.a.createElement(g.b,{direction:"vertical"},e.a.createElement(o.a.Text,null,e.a.createElement(o.a.Text,{strong:!0},"type1\uFF1A"),e.a.createElement(o.a.Text,null,"\u6309\u7167\u6267\u884C\u7ED3\u679C\u4E3A\u4F9D\u636E\u5C55\u793A")),e.a.createElement(g.b,null,e.a.createElement(o.a.Text,{strong:!0},"\u62E5\u6709\u72B6\u6001\uFF1A"),e.a.createElement(p.a,{color:"#81BF84"},"Complete"),e.a.createElement(p.a,{color:"#649FF6"},"Running"),e.a.createElement(p.a,{color:"#C84C5A"},"Fail"),e.a.createElement(p.a,{color:"#D9D9D9",style:{color:"#1d1d1d"}},"Pending"),e.a.createElement(p.a,{color:"#D9D9D9",style:{color:"#1d1d1d"}},"Stop"),e.a.createElement(p.a,{color:"#D9D9D9",style:{color:"#1d1d1d"}},"Skip")),e.a.createElement(o.a.Text,null,e.a.createElement(o.a.Text,{strong:!0},"type2\uFF1A"),e.a.createElement(o.a.Text,null,"\u6309\u7167case\u7ED3\u679C\u4E3A\u4F9D\u636E\u5C55\u793A")),e.a.createElement(g.b,null,e.a.createElement(o.a.Text,{strong:!0},"\u62E5\u6709\u72B6\u6001\uFF1A"),e.a.createElement(p.a,{color:"#81BF84"},"Pass"),e.a.createElement(p.a,{color:"#649FF6"},"Running"),e.a.createElement(p.a,{color:"#C84C5A"},"Fail"),e.a.createElement(p.a,{color:"#D9D9D9",style:{color:"#1d1d1d"}},"Pending"),e.a.createElement(p.a,{color:"#D9D9D9",style:{color:"#1d1d1d"}},"Stop")))}))))},Ie=Fe,ce,ie,de,me,X=Object(A.a)(Z.a)(ce||(ce=Object(y.a)([`
    margin-top:16px;
    &:first-child {
        margin-top:0px;
    }
`]))),ve=Object(A.a)(S.a)(ie||(ie=Object(y.a)([`
    text-align:right;
`]))),w=Object(A.a)(o.a.Text)(de||(de=Object(y.a)([`
    margin-left:9px;
`]))),Be=Object(A.a)(o.a.Text)(me||(me=Object(y.a)([`
    position: relative;
    /* top: -5px;
    left: -5px; */
`]))),We=function(m){var W=Object(i.h)(),P=W.ws_id,Y=Object(n.useState)(!1),L=Object(f.a)(Y,2),_=L[0],R=L[1],k=Object(n.useState)(!0),N=Object(f.a)(k,2),Le=N[0],Ee=N[1],Ue=Object(n.useState)("0"),pe=Object(f.a)(Ue,2),q=pe[0],ge=pe[1],Ke=Object(n.useState)({}),fe=Object(f.a)(Ke,2),ee=fe[0],ze=fe[1],Je=Object(n.useState)(0),Oe=Object(f.a)(Je,2),U=Oe[0],te=Oe[1],$e=Object(n.useState)(0),De=Object(f.a)($e,2),V=De[0],Ge=De[1],He=Object(n.useState)(0),ye=Object(f.a)(He,2),Q=ye[0],he=ye[1],Ye=e.a.useMemo(function(){var v=U,l=Q*60,E=V*24*60;V===7&&(U||Q)&&(te(0),he(0));var c=E+l+v;return Ee(c<5||c===+ee.recover_server_protect_duration),c},[U,V,Q]),ae=function(){var v=Object(B.a)(a.a.mark(function l(){var E,c,C,T;return a.a.wrap(function(r){for(;;)switch(r.prev=r.next){case 0:return R(!0),r.next=3,je({ws_id:P});case 3:if(E=r.sent,c=E.data,C=E.code,T=E.msg,C===200){r.next=9;break}return r.abrupt("return",I.default.warning(T));case 9:ze(c),ge(c.auto_recover_server),te(parseInt(c.recover_server_protect_duration)),R(!1);case 13:case"end":return r.stop()}},l)}));return function(){return v.apply(this,arguments)}}(),Ce=function(){var v=Object(B.a)(a.a.mark(function l(E){var c,C,T;return a.a.wrap(function(r){for(;;)switch(r.prev=r.next){case 0:return R(!0),r.next=3,oe(Object(j.a)({ws_id:P},E));case 3:if(c=r.sent,C=c.code,T=c.msg,C===200){r.next=9;break}return R(!1),r.abrupt("return",I.default.warning(T));case 9:ae(),Ee(!0);case 11:case"end":return r.stop()}},l)}));return function(E){return v.apply(this,arguments)}}(),Ne=function(){var v=Object(B.a)(a.a.mark(function l(E){var c,C,T;return a.a.wrap(function(r){for(;;)switch(r.prev=r.next){case 0:return R(!0),r.next=3,oe(Object(j.a)(Object(j.a)({ws_id:P},ee),E));case 3:if(c=r.sent,C=c.code,T=c.msg,C===200){r.next=9;break}return R(!1),r.abrupt("return",I.default.warning(T));case 9:ae();case 10:case"end":return r.stop()}},l)}));return function(E){return v.apply(this,arguments)}}(),Ve=function(l){Ce({auto_recover_server:l.target.value}),ge(l.target.value)},Qe=function(){Ce({auto_recover_server:q,recover_server_protect_duration:"".concat(U)})};return Object(n.useEffect)(function(){ae()},[]),e.a.createElement(b.a,{spinning:_},e.a.createElement(Se.a,{title:e.a.createElement(M.b,{id:"Workspace.".concat(m.route.name)})},e.a.createElement(X,{gutter:20},e.a.createElement(ve,{span:4},e.a.createElement(o.a.Text,null,"broken\u673A\u5668\u81EA\u52A8\u6062\u590D\uFF1A")),e.a.createElement(S.a,{span:20},e.a.createElement(u.a.Group,{onChange:Ve,value:q},e.a.createElement(u.a,{value:"1"},"\u662F"),e.a.createElement(u.a,{value:"0"},"\u5426")))),q=="1"&&e.a.createElement(e.a.Fragment,null,e.a.createElement(X,{gutter:20},e.a.createElement(ve,{span:4},e.a.createElement(o.a.Text,null,"\u65F6\u95F4\uFF1A")),e.a.createElement(S.a,{span:20},e.a.createElement(g.b,{align:"center"},e.a.createElement(o.a.Text,null,e.a.createElement(D.a,{size:"small",min:0,max:7,style:{width:60},value:V,onChange:function(l){return Ge(typeof l=="number"?l:0)}}),e.a.createElement(w,null,"\u5929")),e.a.createElement(o.a.Text,null,e.a.createElement(D.a,{size:"small",min:0,max:23,style:{width:60},value:Q,onChange:function(l){return he(typeof l=="number"?l:0)}}),e.a.createElement(w,null,"\u65F6")),e.a.createElement(o.a.Text,null,e.a.createElement(D.a,{size:"small",min:0,max:59,style:{width:60},value:U,onChange:function(l){return te(typeof l=="number"?l:0)}}),e.a.createElement(w,null,"\u5206\u949F")),e.a.createElement(o.a.Text,null,"="),e.a.createElement(o.a.Text,null,Ye,"\u5206\u949F"),e.a.createElement(Be,null,e.a.createElement(s.a,{title:"",desc:"\u6700\u77ED\u6062\u590D\u65F6\u95F45\u5206\u949F\uFF0C\u6700\u957F\u6062\u590D\u65F6\u95F47\u5929"}))))),e.a.createElement(X,{gutter:20},e.a.createElement(S.a,{span:20,offset:4},e.a.createElement(g.b,{size:"large"},e.a.createElement(O.a,{size:"small",type:"primary",onClick:Qe,disabled:Le},"\u66F4\u65B0"))))),e.a.createElement(Ie,{field:"func_result_view_type",dataSource:ee,update:Ne})))},Xe=d.default=We},"en/e":function(K,d,t){"use strict";t.d(d,"c",function(){return F}),t.d(d,"b",function(){return u}),t.d(d,"a",function(){return $});var ne=t("IzEo"),b=t("bx4M"),x=t("qqnG"),O=t("vOnD"),z,g,J,D,F=Object(O.a)(b.a)(z||(z=Object(x.a)([`
    border:none !important;
    .ant-card-head {
        min-height: 48px;
        .ant-tabs-tab { min-height : 48px; }
        .ant-card-head-title{
            padding: 0;
        }
        .ant-card-extra {
            padding: 0;
        }
    }
    .common_pagination { padding-bottom:0 ;}
`]))),u=Object(O.a)(F)(g||(g=Object(x.a)([`
    border:none!important;
    .ant-card-head .ant-card-head-wrapper { min-height:48px; }
    .ant-card-head-title { font-weight: normal; font-size:14px;}
    .commom_pagination { margin-bottom:0 ;}
    .ant-tabs-nav { margin : 0 ;}
    .ant-spin-nested-loading > div > .ant-spin {
        position: fixed;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
    }
`]))),j=Object(O.a)(b.a)(J||(J=Object(x.a)([`
    border:none !important;
    .ant-card-head {
        min-height: 48px;
        padding: 0 32px;
        .ant-tabs-tab { min-height : 48px; }
        .ant-card-head-title{
            padding: 0;
        }
        .ant-card-extra {
            padding: 0;
        }
    }
    .ant-card-body{
        padding: 24px 24px 24px 0px;
    }
    .common_pagination { padding-bottom:0 ;}
`]))),$=Object(O.a)(j)(D||(D=Object(x.a)([`
    border:none!important;
    .ant-card-head .ant-card-head-wrapper { min-height:48px; }
    .ant-card-head-title { font-weight: normal; font-size:14px;}
    .commom_pagination { margin-bottom:0 ;}
    .ant-tabs-nav { margin : 0 ;}
    .ant-spin-nested-loading > div > .ant-spin {
        position: fixed;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
    }
`])))},qTtT:function(K,d,t){"use strict";t.d(d,"d",function(){return re}),t.d(d,"a",function(){return o}),t.d(d,"b",function(){return le}),t.d(d,"c",function(){return y});var ne=t("OaEy"),b=t("2fM7"),x=t("DYRE"),O=t("zeV3"),z=t("5Dmo"),g=t("3S7+"),J=t("+BJd"),D=t("mr32"),F=t("q1tI"),u=t.n(F),j=t("Lyp1"),$=t("TSYQ"),I=t.n($),B=t("u+WS"),f=t.n(B),re=function(a){var n,e,i=a.label,M=a.closable,s=a.onClose,G=a.value;return u.a.createElement(D.a,{color:(n=i.props)===null||n===void 0?void 0:n.color,closable:M,onClose:s,style:{marginRight:3}},((e=i.props)===null||e===void 0?void 0:e.children)||G)},o=function(a){var n=a.title,e=a.desc,i=a.className;return u.a.createElement(O.b,null,u.a.createElement("span",{style:{color:"rgba(0, 0, 0, 0.85)"}},n),u.a.createElement(g.a,{overlayClassName:I()(f.a.table_question_tooltip,i),placement:"bottom",arrowPointAtCenter:!0,title:e,color:"#fff"},u.a.createElement(j.a,{style:{color:"rgba(0, 0, 0, 0.65)"}})))},le=function(a,n){return a.map(function(e){return u.a.createElement(b.a.Option,{value:e.id,key:e.id},e[n])})},S=function(a,n){return a.map(function(e){return u.a.createElement(b.a.Option,{value:e.id,key:e.id},"".concat(e[n],"\uFF08").concat(e.state,"\uFF09"))})},be=function(a,n,e){for(var i="",M=a.length,s=0;s<M;s++)if(a[s].id===n){i=a[s][e];break}return i},Z=function(a,n,e){for(var i="",M=a.length,s=0;s<M;s++)if(a[s].id===n){i=a[s][e].indexOf(" / ")>-1?a[s][e]:"".concat(a[s].pub_ip," / ").concat(a[s][e]);break}return i},y=function(a){if(a&&JSON.stringify(a)!=="{}"){for(var n=Object.keys(a),e=0,i=n.length;e<i;e++)if(a[n[e]].length>1)return!0}return!1}},"u+WS":function(K,d,t){K.exports={job_test_form:"job_test_form___9jbiJ",save_template:"save_template___1y982",table_question_tooltip:"table_question_tooltip___3qPEG"}}}]);
