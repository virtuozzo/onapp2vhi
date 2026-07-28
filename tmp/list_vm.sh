#!/bin/bash

TENANT_ID=` openstack project list | grep admin | awk '{print $2}' `

TOKEN=` curl -ksD - -o /dev/null -H 'Content-Type: application/json' -d '
{
  "auth": {
    "identity": {
      "methods": [
        "password"
      ],
      "password": {
        "user": {
          "name": "admin",
          "domain": {
            "id": "default"
          },
          "password": "your_admin_password"
        }
      }
    },
    "scope": {
      "project": {
        "name": "admin",
        "domain": {
          "id": "default"
        }
      }
    }
  }
}' https://vzvhi.onapp.virtuozzo.com:5000/v3/auth/tokens | grep X-Subject-Token: | awk '{print $2}'`

#echo "$TOKEN"
#echo "$TENANT_ID"

curl -ks -H 'Content-Type: application/json' -H 'X-Auth-Token: '$TOKEN https://vzvhi.onapp.virtuozzo.com:8774/v2.1/$TENANT_ID/servers?all_tenants

echo ''

